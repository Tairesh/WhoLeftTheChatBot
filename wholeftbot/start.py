import logging
import os
from argparse import ArgumentParser
from logging.handlers import TimedRotatingFileHandler

from wholeftbot.database import Database
from wholeftbot.telegrambot import TelegramBot


def _parse_args():
    """
    Parse command line arguments
    :return:
    """
    parser = ArgumentParser(description="WhoLeftBot")

    parser.add_argument(
        "--log",
        dest="logfile",
        help="path to logfile",
        default=os.path.join("log", "wholeftbot.log"),
        required=False,
        metavar="FILE",
    )

    parser.add_argument(
        "--lvl",
        dest="loglevel",
        type=int,
        choices=[0, 10, 20, 30, 40, 50],
        help="Disabled, Debug, Info, Warning, Error, Critical",
        default=30,
        required=False,
    )

    parser.add_argument(
        "--no-logfile",
        dest="savelog",
        action="store_false",
        help="don't save logs to file",
        required=False,
        default=True,
    )

    parser.add_argument(
        "--clean",
        dest="clean",
        action="store_true",
        help="clean any pending telegram updates before polling",
        required=False,
        default=False,
    )

    parser.add_argument(
        "--token", dest="token", help="Telegram bot token", required=True, default=None
    )

    parser.add_argument(
        "--db",
        dest="database",
        help="path to SQLite database file",
        default=os.path.join("database", "wholeftbot.sqlite"),
        required=False,
        metavar="FILE",
    )

    parser.add_argument(
        "--debug",
        dest="debug",
        help="run TeleBot in debug mode",
        action="store_true",
        required=False,
        default=False,
    )

    return parser.parse_args()


class WhoLeftBot:
    def __init__(self):
        self.args = _parse_args()
        self._init_logger(self.args.logfile, self.args.loglevel)
        self.db = Database(self.args.database)
        self.tgbot = TelegramBot(
            self.args.token,
            self.db,
            self.args.clean,
            self.args.debug,
        )

    def _init_logger(self, logfile, level):
        """
        Configure logger
        :param logfile:
        :param level:
        :return:
        """
        logger = logging.getLogger()
        logger.setLevel(level)

        log_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

        # Log to console
        console_log = logging.StreamHandler()
        console_log.setFormatter(logging.Formatter(log_format))
        console_log.setLevel(level)

        logger.addHandler(console_log)

        # Save logs if enabled
        if self.args.savelog:
            # Create 'log' directory if not present
            log_path = os.path.dirname(logfile)
            if not os.path.exists(log_path):
                os.makedirs(log_path)

            file_log = TimedRotatingFileHandler(logfile, when="H", encoding="utf-8")

            file_log.setFormatter(logging.Formatter(log_format))
            file_log.setLevel(level)

            logger.addHandler(file_log)

    def start(self):
        self.tgbot.bot_start_polling()
        self.tgbot.bot_idle()
