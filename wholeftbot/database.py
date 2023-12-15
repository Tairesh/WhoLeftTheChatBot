import os
import sqlite3
from typing import Optional, Set, List

from telebot.types import User as TelegramUser, Chat as TelegramChat


class User:
    def __init__(self, row):
        (
            self.id,
            self.first_name,
            self.last_name,
            self.username,
            self.language,
            self.created_at,
        ) = row


class Chat:
    def __init__(self, row):
        (
            self.chat_id,
            self.type,
            self.title,
            self.username,
            self.created_at,
        ) = row


class Database:
    SQL_DB_EXISTS = "SELECT name FROM sqlite_master"
    SQL_CREATE_USERS = """CREATE TABLE users (
        user_id INTEGER NOT NULL PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT,
        username TEXT,
        language TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )"""
    SQL_CREATE_USERS_NAME_INDEX = (
        """CREATE UNIQUE INDEX IF NOT EXISTS users_username ON users (username)"""
    )
    SQL_CREATE_CHATS = """CREATE TABLE chats (
        chat_id INTEGER NOT NULL PRIMARY KEY,
        type TEXT NOT NULL,
        title TEXT,
        username TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )"""
    SQL_CREATE_CMD_DATA = """CREATE TABLE cmd_data (
        user_id INTEGER NOT NULL,
        chat_id INTEGER,
        command TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(chat_id) REFERENCES chats(chat_id)
    )"""
    SQL_CREATE_LEFT_MEMBER_LOG = """CREATE TABLE left_member_log (
        user_id INTEGER NOT NULL,
        chat_id INTEGER NOT NULL ,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(chat_id) REFERENCES chats(chat_id)
    )"""

    SQL_USER_EXISTS = """SELECT EXISTS (
        SELECT 1 FROM users WHERE user_id = ?
    )"""
    SQL_USER_ADD = "INSERT INTO users (user_id, first_name, last_name, username, language) VALUES (?, ?, ?, ?, ?)"
    SQL_USER_DELETE = "DELETE FROM users WHERE user_id = ?"
    SQL_USER_UPDATE = "UPDATE users SET first_name = ?, last_name = ?, username = ?, language = ? WHERE user_id = ?"
    SQL_USER_GET = (
        "SELECT user_id, first_name, last_name, username, language, created_at "
        "FROM users WHERE user_id = ?"
    )
    SQL_USER_GET_BY_UN = (
        "SELECT user_id, first_name, last_name, username, language, created_at "
        "FROM users WHERE lower(username) = ?"
    )
    SQL_USERS_GET = (
        "SELECT user_id, first_name, last_name, username, language, created_at "
        "FROM users WHERE user_id IN ({})"
    )

    SQL_CHAT_EXISTS = """SELECT EXISTS (
        SELECT 1 FROM chats WHERE chat_id = ?
    )"""
    SQL_CHAT_ADD = (
        "INSERT INTO chats (chat_id, type, title, username) VALUES (?, ?, ?, ?)"
    )
    SQL_CHAT_UPDATE = (
        "UPDATE chats SET type = ?, title = ?, username = ? WHERE chat_id = ?"
    )
    SQL_CHAT_GET = (
        "SELECT chat_id, type, title, username, created_at FROM chats WHERE chat_id = ?"
    )

    SQL_CMD_ADD = "INSERT INTO cmd_data (user_id, chat_id, command) VALUES (?, ?, ?)"
    SQL_MEMBER_LEFT_ADD = "INSERT INTO left_member_log (user_id, chat_id) VALUES (?, ?)"
    SQL_MEMBER_LEFT_GET = """SELECT u.user_id, first_name, last_name, username, language, left_member_log.created_at 
        FROM left_member_log LEFT JOIN users u on left_member_log.user_id = u.user_id 
        WHERE chat_id = ? AND left_member_log.created_at BETWEEN datetime('now', ?) AND datetime('now', 'localtime')
        GROUP BY u.user_id;
    """

    def __init__(self, db_path):
        self._db_path = db_path

        # Create 'data' directory if not present
        data_dir = os.path.dirname(db_path)
        os.makedirs(data_dir, exist_ok=True)

        con = sqlite3.connect(db_path)
        cur = con.cursor()

        # If tables don't exist, create them
        tables = set([row[0] for row in cur.execute(self.SQL_DB_EXISTS).fetchall()])
        if "users" not in tables:
            cur.execute(self.SQL_CREATE_USERS)
            cur.execute(self.SQL_CREATE_USERS_NAME_INDEX)
        if "chats" not in tables:
            cur.execute(self.SQL_CREATE_CHATS)
        if "cmd_data" not in tables:
            cur.execute(self.SQL_CREATE_CMD_DATA)
        if "left_member_log" not in tables:
            cur.execute(self.SQL_CREATE_LEFT_MEMBER_LOG)
        con.commit()

        con.close()

    def save_user_and_chat(self, user: TelegramUser, chat: Optional[TelegramChat]):
        """
        Save user and / or chat to database
        :param user: User
        :param chat: Chat
        :return:
        """
        con = sqlite3.connect(self._db_path)
        cur = con.cursor()

        # Check if user already exists
        cur.execute(self.SQL_USER_EXISTS, [user.id])
        # Add user if he doesn't exist
        if cur.fetchone()[0] != 1:
            # Hack to avoid duplicated usernames bag
            user_with_same_username = self.get_user_by_username(user.username)
            if user_with_same_username is not None:
                cur.execute(self.SQL_USER_DELETE, [user_with_same_username.id])
                con.commit()
            cur.execute(
                self.SQL_USER_ADD,
                (
                    user.id,
                    user.first_name,
                    user.last_name,
                    user.username,
                    user.language_code,
                ),
            )
            con.commit()
        else:
            cur.execute(
                self.SQL_USER_UPDATE,
                (
                    user.first_name,
                    user.last_name,
                    user.username,
                    user.language_code,
                    user.id,
                ),
            )
            con.commit()

        chat_id = None

        if chat and chat.id != user.id:
            chat_id = chat.id

            # Check if chat already exists
            cur.execute(self.SQL_CHAT_EXISTS, (chat.id,))

            con.commit()

            # Add chat if it doesn't exist
            if cur.fetchone()[0] != 1:
                cur.execute(
                    self.SQL_CHAT_ADD, (chat.id, chat.type, chat.title, chat.username)
                )
                con.commit()
            else:
                cur.execute(
                    self.SQL_CHAT_UPDATE,
                    (chat.type, chat.title, chat.username, chat.id),
                )
                con.commit()

        con.close()

        return user.id, chat_id

    def save_cmd(self, user, chat, cmd):
        user_id, chat_id = self.save_user_and_chat(user, chat)

        con = sqlite3.connect(self._db_path)
        cur = con.cursor()

        # Save issued command
        cur.execute(self.SQL_CMD_ADD, (user_id, chat_id, cmd))

        con.commit()
        con.close()

    def left_member_log(self, user, chat):
        user_id, chat_id = self.save_user_and_chat(user, chat)

        con = sqlite3.connect(self._db_path)
        cur = con.cursor()

        cur.execute(self.SQL_MEMBER_LEFT_ADD, (user_id, chat_id))

        con.commit()
        con.close()

    def get_user(self, user_id: int) -> Optional[User]:
        con = sqlite3.connect(self._db_path)
        cur = con.cursor()
        cur.execute(self.SQL_USER_GET, (user_id,))
        row = cur.fetchone()
        con.close()
        return User(row) if row else None

    def get_users(self, users_ids: Set[int]) -> List[User]:
        con = sqlite3.connect(self._db_path)
        cur = con.cursor()
        cur.execute(self.SQL_USERS_GET.format(",".join(map(str, users_ids))))
        rows = cur.fetchall()
        con.close()
        return [User(row) for row in rows]

    def get_user_by_username(self, username: str) -> Optional[User]:
        con = sqlite3.connect(self._db_path)
        cur = con.cursor()
        cur.execute(self.SQL_USER_GET_BY_UN, (username,))
        row = cur.fetchone()
        con.close()
        return User(row) if row else None

    def get_chat(self, chat_id: int) -> Optional[Chat]:
        con = sqlite3.connect(self._db_path)
        cur = con.cursor()
        cur.execute(self.SQL_CHAT_GET, (chat_id,))
        row = cur.fetchone()
        con.close()
        return Chat(row) if row else None

    def get_left_members(self, chat_id: int, datetime_param: str) -> List[User]:
        con = sqlite3.connect(self._db_path)
        cur = con.cursor()
        cur.execute(self.SQL_MEMBER_LEFT_GET, (chat_id, datetime_param))
        rows = cur.fetchall()
        con.close()
        return [User(row) for row in rows]
