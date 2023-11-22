from mautrix.types import EventType
from maubot import Plugin, MessageEvent
from maubot.handlers import event


class HelloWorldBot(Plugin):
    @event.on(EventType.ROOM_MESSAGE)
    async def handler(self, message: MessageEvent) -> None:
        if not message.content.body.startswith("Hello, World!"):
            await message.reply("Hello, World!")
