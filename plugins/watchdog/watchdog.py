from maubot import Plugin
from mautrix.types import RoomID, DirectoryPaginationToken
from mautrix.types.misc import PublicRoomInfo
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from typing import Type, List, Dict
import asyncio


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("room")
        helper.copy("monitoring_interval")


class WatchDog(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor_rooms_task = None  # hold task object
        self._cache_room_details = {}

    def get_command_name(self) -> str:
        return self.id

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    async def start(self) -> None:
        await super().start()
        self.config.load_and_update()

        await self.post_notice("🔔 watchdog now running")

        # Don't forget to cancel the task, when stopping
        self.monitor_rooms_task = self.loop.create_task(self.monitor_rooms())

    async def pre_stop(self) -> None:
        if self.monitor_rooms_task is not None and not self.monitor_rooms_task.done():
            self.monitor_rooms_task.cancel()
        await self.post_notice("🔔 watchdog shutting down")

    def get_room_from_config(self) -> RoomID:
        return RoomID(self.config["room"])

    def get_monitoring_interval_from_config(self) -> int:
        return self.config["monitoring_interval"]

    async def monitor_rooms(self) -> None:
        # can't do anything without having an initial list,
        # so high max_retries effectively not really needing to catch exception
        known_rooms = await self.query_room_dir(max_retries=999)
        known_rooms_ids = known_rooms.keys()

        while True:
            try:
                current_rooms = await self.query_room_dir(max_retries=5)
                current_rooms_ids = current_rooms.keys()

                # figure out rooms added/removed
                rooms_removed = list(set(known_rooms_ids) - set(current_rooms_ids))
                rooms_added = list(set(current_rooms_ids) - set(known_rooms_ids))

                await self.handle_room_changes(rooms_removed, "➖ Rooms removed:")
                await self.handle_room_changes(rooms_added, "➕ Rooms added:")

                # figure out changes in rooms' name or topic
                await self.handle_room_meta_changes(known_rooms, current_rooms)

                # update new state as known state
                known_rooms = current_rooms
                known_rooms_ids = current_rooms_ids

            except Exception as e:
                self.log.exception("failed to fetch room dir while monitoring")

            await asyncio.sleep(self.get_monitoring_interval_from_config())

    async def handle_room_changes(self, room_list: List[RoomID], message_prefix: str) -> None:
        if room_list:
            text_message = f"**{message_prefix}**\n"
            html_message = f"<strong>{message_prefix}</strong><br><ul>"
            for room_id in room_list:
                text_message += f"{self._cache_room_details[room_id].name} `{room_id}`\n"
                html_message += f"<li>{self._cache_room_details[room_id].name} <code>{room_id}</code></li>"
            html_message += f"</ul>"
            await self.post_message(text_message, html_message)

    async def handle_room_meta_changes(self, known_rooms: Dict[RoomID, PublicRoomInfo],
                                       current_rooms: Dict[RoomID, PublicRoomInfo]):
        for room_id in current_rooms:
            if room_id in known_rooms and current_rooms[room_id].name != known_rooms[room_id].name:
                text_message = (
                    f"**Room name update:**\n`{known_rooms[room_id].name}` -> `{current_rooms[room_id].name}`"
                    f"`{room_id}`")
                html_message = (
                    f"<strong>Room name update:</strong><br><code>{known_rooms[room_id].name}</code> -> "
                    f"<code>{current_rooms[room_id].name}</code><br><code>{room_id}</code>"
                )
                await self.post_message(text_message, html_message)

                if room_id in known_rooms and current_rooms[room_id].topic != known_rooms[room_id].topic:
                    text_message = (
                        f"**Room topic update:**\n`{current_rooms[room_id].name}`\n`{known_rooms[room_id].topic}` ->"
                        f" `{current_rooms[room_id].topic}` `{room_id}`"
                    )
                html_message = (
                    f"<strong>Room topic update:</strong><br><code>{current_rooms[room_id].name}</code><br>"
                    f"Old topic: <code>{known_rooms[room_id].topic}</code><br>"
                    f"New topic:<code>{current_rooms[room_id].topic}</code><br><code>{room_id}</code>"
                )
                await self.post_message(text_message, html_message)

    async def query_room_dir(self, max_retries) -> Dict[RoomID, PublicRoomInfo]:
        all_rooms = {}

        retries = 0
        base_delay = 10
        max_delay = 1800  # 30mins

        pagination_token = DirectoryPaginationToken("")

        # infinite loop since we need to loop over paginated results as well as upon failures (exceptions)
        while True:
            delay = min(base_delay * 2 ** retries, max_delay)

            try:
                directory = await self.client.get_room_directory(
                    limit=1000,
                    include_all_networks=False,
                    since=pagination_token
                )
            except Exception as e:
                if retries < max_retries:
                    self.log.exception("failed to query room directory but will retry")
                    await asyncio.sleep(delay)

                    retries += 1
                    continue
                else:
                    self.log.exception("failed to query room directory & exhausted max_retries")
                    raise

            retries = 0

            if len(directory.chunk) > 0:
                for room in directory.chunk:
                    all_rooms[room.room_id] = room
                    self._cache_room_details[room.room_id] = room

            if directory.next_batch is None:
                break

            pagination_token = directory.next_batch

        return all_rooms

    async def post_message(self, text, html=None):
        await self.client.send_text(room_id=self.get_room_from_config(), text=text, html=html)

    async def post_notice(self, text, html=None):
        await self.client.send_notice(room_id=self.get_room_from_config(), text=text, html=html)
