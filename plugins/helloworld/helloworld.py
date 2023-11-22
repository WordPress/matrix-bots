from mautrix.types import EventType
from maubot import Plugin, MessageEvent
from maubot.handlers import event


class HelloWorldBot(Plugin):
    @event.on(EventType.ROOM_MESSAGE)
    async def handler(self, message: MessageEvent) -> None:
        if message.sender != self.client.mxid:
            await message.reply("Hello, World!")
