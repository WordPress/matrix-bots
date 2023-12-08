import json

import aiohttp
from aiohttp import ClientResponse
from maubot import Plugin, MessageEvent
from maubot.handlers import event
from mautrix.types import EventType
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from typing import Type


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("webhook")
        helper.copy("secret")


class Relay(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._room_directory_cache = None

    def get_command_name(self) -> str:
        return self.id

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    async def start(self) -> None:
        await super().start()
        self.config.load_and_update()

    def get_webhook_from_config(self) -> str:
        return self.config["webhook"]

    def get_secret_from_config(self) -> str:
        return self.config["secret"]

    async def get_room_name_and_alias_by_id(self, room_id: str) -> (str, str):
        if self._room_directory_cache is None:
            directory = await self.client.get_room_directory(limit=1000)
            self._room_directory_cache = directory.chunk

        for room_listing in self._room_directory_cache:
            if room_id == room_listing.room_id:
                return room_listing.name, room_listing.canonical_alias

        return "", ""

    @event.on(EventType.ROOM_MESSAGE)
    async def handle_message(self, evt: MessageEvent) -> None:
        # Ignore messages sent by the bot
        if evt.sender == self.client.mxid:
            return

        # Don't handle commands
        # `//command` is also sent as `/command`
        if evt.content.body.startswith("!") or evt.content.body.startswith("/"):
            return

        # Send message content as HTTP request
        async with aiohttp.ClientSession() as session:
            # prepare payload for webhook request
            room_name, room_alias = await self.get_room_name_and_alias_by_id(evt.room_id)
            thread_root = ""
            if str(evt.content.relates_to.rel_type) == "m.thread":
                thread_root = evt.content.relates_to.event_id

            # Note: room_name and room_alias can be empty if room isn't published in room directory
            payload = aiohttp.FormData({
                "secret": self.get_secret_from_config(),
                "room_id": evt.room_id,
                "room_name": room_name,
                "room_alias": room_alias,
                "event_id": evt.event_id,
                "thread_root": thread_root,
                "timestamp": evt.timestamp,
                "user_id": evt.sender,
                "text": evt.content.body,
            })

            self.log.debug("sending request to %s for evt: %s", self.get_webhook_from_config(), evt.event_id)

            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            async with session.post(self.get_webhook_from_config(), headers=headers, data=payload) as response:
                await self.respond(evt, response)

    # Expected reply fields in JSON response:
    # `messages` or `message` that should be posted to room
    # `reply_in_thread` as true or false - whether reply should be posted directly in room or in thread
    # Note: if event was already in thread, it would always be posted in the thread
    async def respond(self, evt: MessageEvent, response: ClientResponse):
        if response.status != 200 and response.status != 204:
            self.log.debug(f"webhook failure: [%s] %s for event: %s",
                           response.status, await response.text(), evt.event_id)
            return

        content_type = response.headers.get('Content-Type', '').lower()
        if "application/json" not in content_type:
            return

        try:
            content = await response.json()
        except json.JSONDecodeError:
            self.log.debug(f"failed to decode json response `%s` for event: %s",
                           response.content, evt.event_id)
            return

        reply_in_thread = content.get("reply_in_thread", False)
        if str(evt.content.relates_to.rel_type) == "m.thread":
            reply_in_thread = True

        messages = content.get("messages", [])
        if messages:
            for message in messages:
                await evt.respond(content=message, markdown=True, in_thread=reply_in_thread)
            return

        if "message" in content:
            await evt.respond(content=content["message"], markdown=True, in_thread=reply_in_thread)
