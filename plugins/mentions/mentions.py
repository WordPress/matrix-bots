from maubot import Plugin, MessageEvent
from maubot.handlers import event
from mautrix.types import EventType
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from typing import Type, List
import re


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("groups")


class Mentions(Plugin):
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

    def get_groups_from_config(self) -> str:
        return self.config["groups"]

    def get_users_of_group(self, group_name) -> List[str]:
        for group in self.config["groups"]:
            if group['keyword'] == group_name:
                return group['users']

    def get_mentioned_groups(self, text) -> List[str]:
        mentioned_groups = []

        # build regex to search for all group names
        possible_mentions = []
        for group in self.get_groups_from_config():
            possible_mentions.append('@' + group['keyword'])

        specific_mentions_regex = '|'.join(re.escape(possible_mention) for possible_mention in possible_mentions)
        pattern = f'({specific_mentions_regex})'

        matches = re.findall(pattern, text)
        for match in matches:
            mentioned_groups.append(match.split('@')[1])

        return mentioned_groups

    @event.on(EventType.ROOM_MESSAGE)
    async def handle_message(self, evt: MessageEvent) -> None:
        # Ignore messages sent by the bot
        if evt.sender == self.client.mxid:
            return

        # Don't handle commands
        # `//command` is also sent as `/command`
        if evt.content.body.startswith("!") or evt.content.body.startswith("/"):
            return

        # Any group mentions to handle?
        matches = self.get_mentioned_groups(evt.content.body)
        if not matches:
            return

        users_to_notify = {}
        for group in matches:
            for user in self.get_users_of_group(group):
                users_to_notify[user] = True

        await self.notify_users(list(users_to_notify.keys()), matches, evt)

    async def notify_users(self, users, groups, event):
        # get group names
        group_names = []
        groups_config = self.get_groups_from_config()
        for group_config in groups_config:
            for group in groups:
                if group_config['keyword'] == group:
                    group_names.append(group_config['name'])

        formatted_body = "Pinging members of " + ', '.join(group_names) + ": "
        for user in users:
            formatted_body = formatted_body + " \u003ca href='https://matrix.to/#/" + user + "'\u003e" + user + "\u003c/a\u003e"

        # by default this quotes the reply where groups are mentioned
        content = {
            "body": "Pinging members of " + ','.join(groups),
            "format": "org.matrix.custom.html",
            "formatted_body": formatted_body,
            "m.mentions": {"user_ids": users},
            "msgtype": "m.notice",
            "m.relates_to": {
                "m.in_reply_to": {
                    "event_id": event.event_id
                }
            }
        }

        # put this in a thread as well, if we are already in a thread
        if str(event.content.relates_to.rel_type) == "m.thread":
            content["m.relates_to"] = {
                "rel_type": "m.thread",
                "event_id": event.content.relates_to.event_id
            }

        await self.client.send_message_event(
            room_id=event.room_id,
            event_type=EventType.ROOM_MESSAGE,
            content=content
        )
