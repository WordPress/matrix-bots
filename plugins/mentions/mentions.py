import asyncio
import aiohttp
import re
from maubot import Plugin, MessageEvent
from maubot.handlers import event
from mautrix.types import EventType
from typing import List, Tuple, Type
from ruamel import yaml
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("groups_config_src")
        helper.copy("sync_config_interval")


# returns default bool if all elements in boolList are not same
def get_collective_behavior(boolList: List[bool], default: bool) -> bool:
    if len(boolList) == 1:
        return boolList[0]

    if all(value == boolList[0] for value in boolList):
        return boolList[0]
    else:
        return default


class Mentions(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sync_config_task = None  # hold sync task object
        self.configured_groups = None  # synced from external src

    def get_command_name(self) -> str:
        return self.id

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    async def start(self) -> None:
        await super().start()
        self.config.load_and_update()

        # Don't forget to cancel the task, when stopping
        self.sync_config_task = self.loop.create_task(self.sync_config())

    async def pre_stop(self) -> None:
        if self.sync_config_task is not None and not self.sync_config_task.done():
            self.sync_config_task.cancel()

    async def sync_config(self):
        while True:
            src = self.config["groups_config_src"]
            if not src:
                self.log.error("missing config src")
                await asyncio.sleep(self.config["sync_config_interval"])
                continue

            async with aiohttp.ClientSession() as session:
                async with session.get(src) as response:
                    if response.status == 200:
                        self.configured_groups = yaml.safe_load(await response.text())
                    else:
                        self.log.error(f"could not fetch config from src, status={response.status}")
            await asyncio.sleep(self.config["sync_config_interval"])

    def get_groups(self) -> str:
        return self.configured_groups["groups"]

    def get_mentioned_groups(self, text) -> List[str]:
        mentioned_groups = []

        # build regex to search for all group names
        possible_mentions = []
        for group in self.get_groups():
            possible_mentions.append('@' + group['keyword'])
            possible_mentions.append('!subteam^' + group['slack_subteam_id'])

        specific_mentions_regex = '|'.join(re.escape(possible_mention) for possible_mention in possible_mentions)
        pattern = f'({specific_mentions_regex})'

        matches = re.findall(pattern, text)
        for match in matches:
            if match[0] == '@':
                mentioned_groups.append(match.split('@')[1])
            else:
                mentioned_groups.append(match)

        return mentioned_groups

    def get_info_on_matches(self, matches: List[str]) -> Tuple[List[str], List[str], bool, bool]:
        group_names = {}
        users_to_notify = {}

        # choosing behavior
        quote_triggering_message = []
        always_reply_in_thread = []

        for group in self.get_groups():
            for match in matches:
                keyword_match = group['keyword'] == match
                slack_subteam_match = match[0] == '!' and match.split("^")[1] == group['slack_subteam_id']

                if keyword_match or slack_subteam_match:
                    group_names[group['name']] = True
                    for user in group['users']:
                        users_to_notify[user] = True

                    quote_triggering_message.append(bool(group['quote_triggering_message']))
                    always_reply_in_thread.append(bool(group['always_reply_in_thread']))

        return (
            list(users_to_notify.keys()),
            list(group_names.keys()),
            get_collective_behavior(quote_triggering_message, True),
            get_collective_behavior(always_reply_in_thread, False),
        )

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

        # add do_not_bridge property to event so that slack bridge should not carry it over to Slack
        slack_bridge_ignore = False
        for match in matches:
            if match.startswith("!subteam^"):
                slack_bridge_ignore = True

        # collect group names & users to notify
        users_to_notify, group_names, quote_triggering_message, always_reply_in_thread = self.get_info_on_matches(
            matches
        )

        # construct body and formatted_body for message
        body = formatted_body = "Pinging members of " + ', '.join(group_names) + ": "
        body += ", ".join(users_to_notify)
        for user in users_to_notify:
            formatted_body = formatted_body + " <a href='https://matrix.to/#/" + user + "'>" + user + "</a>"

        options = {
            "slack_bridge_ignore": slack_bridge_ignore,
            "quote_triggering_message": quote_triggering_message,
            "always_reply_in_thread": always_reply_in_thread,
            "event": evt
        }

        await self.notify_users(users_to_notify, body, formatted_body, options)

    async def notify_users(self, users: List[str], body: str, formatted_body: str, options: dict):
        evt = options['event']

        content = {
            "body": body,
            "format": "org.matrix.custom.html",
            "formatted_body": formatted_body,
            "m.mentions": {
                "user_ids": users
            },
            "msgtype": "m.notice",
            "m.relates_to": {
                "m.in_reply_to": {
                    "event_id": evt.event_id
                }
            }
        }

        if not options['quote_triggering_message']:
            del content['m.relates_to']

        if options['slack_bridge_ignore']:
            content["org.wordpress.slack_bridge_ignore"] = options['slack_bridge_ignore']

        # put this in a thread as well, if we are already in a thread, replacing in_reply_to
        if str(evt.content.relates_to.rel_type) == "m.thread":
            content["m.relates_to"] = {
                "rel_type": "m.thread",
                "event_id": evt.content.relates_to.event_id
            }
        elif options['always_reply_in_thread']:
            content["m.relates_to"] = {
                "rel_type": "m.thread",
                "event_id": evt.event_id
            }

        try:
            await self.client.send_message_event(
                room_id=evt.room_id,
                event_type=EventType.ROOM_MESSAGE,
                content=content
            )
        except Exception as e:
            self.log.exception("failed to notify users")
