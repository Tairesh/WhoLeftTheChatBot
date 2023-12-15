from typing import List, Optional

from telebot.types import Message

from wholeftbot import emoji
from wholeftbot.commands import Command


class ReloadCommands(Command):
    def get_name(self) -> str:
        return "Reload commands"

    def get_cmds(self) -> List[str]:
        return ["reload"]

    def get_description(self) -> Optional[str]:
        return None

    @Command.only_master
    def call(self, message: Message):
        self.tgb.reload_commands()
        self.bot.reply_to(message, emoji.SHIT + " Reloaded")
