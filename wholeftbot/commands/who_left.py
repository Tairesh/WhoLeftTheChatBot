from typing import List, Optional

from telebot.types import Message

from wholeftbot import emoji, utils
from wholeftbot.commands import Command


class WhoLeft(Command):
    def get_name(self) -> str:
        return "Кто покинул чат?"

    def get_cmds(self) -> List[str]:
        return ["who_left"]

    def get_description(self) -> Optional[str]:
        return "Кто покинул чат?"

    @Command.save_data
    @Command.send_typing
    def call(self, message: Message):
        if message.chat.type == "private":
            return

        users = self.db.get_left_members(message.chat.id, "-1 day")
        if len(users) == 0:
            self.bot.reply_to(message, "За последние сутки никто из чата не выходил! " + emoji.HEART)
            return

        text = emoji.SAD + "За последние сутки из чата вышли:\n"
        for user in users:
            text += utils.user_name(user, mention=True) + "\n"

        self.bot.reply_to(message, text, parse_mode="Markdown")
