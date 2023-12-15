import importlib
import logging
import os
import threading
import traceback
from typing import List

import telebot.types
from telebot import TeleBot
from telebot.types import (
    Message,
    User,
    BotCommand,
)

from wholeftbot import constants, emoji, utils
from wholeftbot.commands import Command
from wholeftbot.database import Database


def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper


class TelegramBot:
    def __init__(self, token, db, clean=False, debug=False):
        self.token: str = token
        self.db: Database = db
        self.clean: bool = clean
        self.debug: bool = debug
        self.commands: List[Command] = []

        self.bot: TeleBot = TeleBot(token, skip_pending=clean)
        self.me: User = self.bot.get_me()
        self.db.save_user_and_chat(self.me, None)

        self._load_commands()

        self.bot.add_message_handler(
            {
                "function": self._handle_text_messages,
                "filters": {
                    "func": lambda m: m.text and not m.forward_from_chat,
                    "content_types": ["text"],
                },
                "pass_bot": False,
            }
        )

        self.bot.add_message_handler(
            {
                "function": self._handle_left_chat_member,
                "filters": {
                    "content_types": ["left_chat_member"],
                },
            }
        )

    # Start the bot
    def bot_start_polling(self):
        for admin in constants.ADMINS:
            self.bot.send_message(admin, emoji.INFO + " I was restarted")

    # Go in idle mode
    def bot_idle(self):
        if self.debug:
            self.bot.polling(True, True)
        else:
            self.bot.infinity_polling()

    def _load_commands(self):
        threads = []

        for _, _, files in os.walk(os.path.join("wholeftbot", "commands")):
            for file in files:
                if not file.lower().endswith(".py"):
                    continue
                if file.startswith("_") or file.startswith("."):
                    continue

                threads.append(self._load_action(file))

        # Make sure that all plugins are loaded
        for thread in threads:
            thread.join()

        commands = []
        for action in self.commands:
            if len(action.get_cmds()) == 0 or not action.get_description():
                continue
            commands.append(BotCommand(action.get_cmds()[0], action.get_description()))
        self.bot.set_my_commands(commands)

    # pylint: disable=W0703
    @threaded
    def _load_action(self, file):
        try:
            module_name = file[:-3]
            module_path = f"wholeftbot.commands.{module_name}"
            module = importlib.import_module(module_path)

            class_name = "".join([s.capitalize() for s in module_name.split("_")])
            action_class = getattr(module, class_name)
            action_class(self).after_loaded()
        except Exception as ex:
            msg = f"File '{file}' can't be loaded as an action: {ex}"
            logging.warning(msg)

    def reload_commands(self):
        for action in self.commands:
            action.after_unload()
        self.commands.clear()
        self._load_commands()

    # Handle all errors
    def _handle_errors(self, message, exception):
        cls_name = f"Class: {type(self).__name__}"
        logging.error(f"{exception} - {cls_name} - {message}")

        error_msg = (
            f"{emoji.ERROR} Exception: <code>{exception.__class__.__name__}</code>\n"
            f"Request: <code>{utils.escape(message.text)}</code>\n"
            f"\n<code>{utils.escape((traceback.format_exc()))}</code>"
        )
        for admin in constants.ADMINS:
            for chunk in utils.chunks(error_msg, 3000):
                self.bot.send_message(admin, chunk, parse_mode="HTML")

    def _handle_text_messages(self, message: Message):
        """
        Handle text messages
        :param message: Message
        :return:
        """
        if not message or not message.text:
            return

        if message.text.startswith("/"):
            at_mention = utils.get_atmention(message)
            if at_mention and at_mention != self.me.username:
                return

            cmd = utils.get_command(message)
            for command in self.commands:
                if cmd in command.get_cmds():
                    command.call(message)
                    return

    def _handle_left_chat_member(self, message: Message):
        """
        Handle left chat member event
        :param message:
        :return:
        """
        user = message.left_chat_member
        if not user:
            return

        chat = message.chat
        if chat.type == "private":
            return

        self.db.left_member_log(user, chat)
