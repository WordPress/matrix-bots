from maubot import Plugin
from maubot.handlers import web
from aiohttp.web import Request, Response
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from mautrix.types import RoomID, RoomAlias
from typing import Type
import json


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("secret")
        helper.copy("homeserver")


class PostToRoom(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_resolved_room_aliases = {}

    def get_command_name(self) -> str:
        return self.id

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    async def start(self) -> None:
        await super().start()
        self.config.load_and_update()

    def get_secret_from_config(self) -> str:
        return self.config["secret"]

    def get_homeserver_from_config(self) -> str:
        return self.config["homeserver"]

    # Available at $MAUBOT_URL/_matrix/maubot/plugin/<instance ID>/notify
    @web.post("/notify")
    async def post_data(self, request: Request) -> Response:
        # avoid stray requests
        if request.rel_url.query["secret"] != self.get_secret_from_config():
            return Response(status=403)

        try:
            data = await request.json()
        except json.JSONDecodeError:
            return Response(status=400, text="error decoding json")

        # Ensure both "room" and "message" are present in the JSON data
        if "room" not in data or "message" not in data:
            return Response(status=400, text="room and message both must be provided")

        room_id = await self.get_room_id(data["room"])
        await self.client.send_markdown(RoomID(room_id), data["message"])
        return Response(status=200)

    # acceptable value for room "where":
    # room alias part such as "core", "#core"
    # room alias such as "#core:community.wordpress.org"
    # room id such as "!cHPvPsHiObbVCkAdiy:community.wordpress.org"
    async def get_room_id(self, where: str) -> str:
        if where[0] == '!':
            return where

        if where[0] != '#':
            room_alias = '#' + where.split(':')[0] + ':' + self.get_homeserver_from_config()
        else:
            room_alias = where.split(':')[0] + ':' + self.get_homeserver_from_config()

        return await self.resolve_room_alias(room_alias)

    async def resolve_room_alias(self, room_alias: str) -> str:
        room_alias_local_part = room_alias[1:].split(':')[0]

        # fetch & cache, if we don't already have it in cache
        if room_alias_local_part not in self._cached_resolved_room_aliases:
            room_alias_info = await self.client.resolve_room_alias(RoomAlias(room_alias))
            self._cached_resolved_room_aliases[room_alias_local_part] = room_alias_info.room_id

        return self._cached_resolved_room_aliases[room_alias_local_part]
