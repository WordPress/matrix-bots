from maubot import Plugin
from mautrix.types import RoomID, DirectoryPaginationToken
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from typing import Type, List
import asyncio


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("room")


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

        # Don't forget to cancel the task, when stopping
        self.monitor_rooms_task = self.loop.create_task(self.monitor_rooms())

    async def pre_stop(self) -> None:
        if self.monitor_rooms_task is not None and not self.monitor_rooms_task.done():
            self.monitor_rooms_task.cancel()

    def get_room_from_config(self) -> RoomID:
        return RoomID(self.config["room"])

    async def monitor_rooms(self) -> None:
        # Get the initial list of rooms on the homeserver
        initial_rooms = await self.get_all_rooms_ids()

        while True:
            current_rooms = await self.get_all_rooms_ids()

            rooms_removed = list(set(initial_rooms) - set(current_rooms))
            rooms_added = list(set(current_rooms) - set(initial_rooms))

            await self.handle_room_changes(rooms_removed, "Rooms removed:")
            await self.handle_room_changes(rooms_added, "Rooms added:")

            initial_rooms = current_rooms
            await asyncio.sleep(300)  # sleep for 5mins

    async def handle_room_changes(self, room_list: List[RoomID], message_prefix: str) -> None:
        if room_list:
            text_message = f"{message_prefix}\n"
            html_message = f"{message_prefix}<br><ul>"
            for room_id in room_list:
                text_message += f"{self._cache_room_details[room_id]} `{room_id}`\n"
                html_message += f"<li>{self._cache_room_details[room_id]} <code>{room_id}</code></li>"
            html_message += f"</ul>"
            await self.client.send_text(room_id=self.get_room_from_config(), text=text_message, html=html_message)

    async def get_all_rooms_ids(self) -> List[RoomID]:
        all_room_ids = []
        pagination_token = DirectoryPaginationToken("")

        while True:
            directory = await self.client.get_room_directory(
                limit=1000,
                include_all_networks=False,
                since=pagination_token
            )
            if len(directory.chunk) > 0:
                for room in directory.chunk:
                    all_room_ids.append(room.room_id)
                    self._cache_room_details[room.room_id] = room.name

            if directory.next_batch is None:
                break

            pagination_token = directory.next_batch

        return all_room_ids
