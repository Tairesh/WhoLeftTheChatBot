import datetime
import html
import re
from typing import Union

from telebot.types import Message, User

from wholeftbot.database import User as DBUser


def get_command(message: Message):
    return message.text.split(" ")[0].split("@")[0][1:].lower()


def get_atmention(message: Message):
    if "@" in message.text:
        command = message.text.split(" ")[0].split("@")
        return command[1] if len(command) > 1 else None
    return None


def chunks(s, n):
    """Produce `n`-long chunks from `s`."""
    for start in range(0, len(s), n):
        yield s[start : start + n]


def user_name(
    user: Union[User, DBUser],
    with_username=False,
    prefer_username=False,
    mention=False,
    mention_type="Markdown",
):
    if prefer_username and user.username:
        return "@" + user.username

    name = user.first_name
    if with_username and user.username:
        name += " @" + user.username
    if user.last_name:
        name += " " + user.last_name

    name = name.replace("ᅠ", "").strip()
    if mention:
        if mention_type.lower().startswith("markdown"):
            name = f"[{markdown_escape(name)}](tg://user?id={user.id})"
        else:
            name = f'<a href="tg://user?id={user.id}">{escape(name)}</a>'

    return name.strip()


def markdown_escape(text):
    markdown_entities = [
        "*",
        "{",
        "}",
        "[",
        "]",
        "(",
        ")",
        "#",
        "+",
        "-",
        ".",
        "!",
        "|",
    ]
    pattern = "|".join(map(re.escape, markdown_entities))

    return re.sub(pattern, r"\\\g<0>", text)


def escape(text: str):
    """Returns the given HTML with ampersands, quotes and carets encoded."""
    return html.escape(text)


def format_number(n: int, s0: str, s1: str, s2: str) -> str:
    result = str(n) + " "
    if n == 0:
        result += s0
    elif n == 1 or (n % 10 == 1 and n != 11 and n % 100 != 11):
        result += s1
    elif n > 100 and 12 <= n % 100 <= 14:
        result += s0
    elif (2 <= n % 10 <= 4 and n > 20) or (2 <= n <= 4):
        result += s2
    else:
        result += s0
    return result


def human_delta_t(dt: datetime.timedelta):
    if dt.total_seconds() <= 0:
        if dt.total_seconds() > -60:
            return "только что"
        elif dt.total_seconds() > -60 * 10:
            return "недавно"
        else:
            return "давно"
    else:
        hours = dt.seconds // (60 * 60)
        minutes = (dt.seconds - (hours * 60 * 60)) // 60
        seconds = dt.seconds - (hours * 60 * 60) - (minutes * 60)
        if dt.days > 0:
            return (
                f"через: {format_number(dt.days, 'дней', 'день', 'дня')} "
                f"{format_number(hours, 'часов', 'час', 'часа')} "
                f"{format_number(minutes, 'минут', 'минута', 'минуты')} "
                f"{format_number(seconds, 'секунд', 'секунда', 'секунды')}"
            )
        elif dt.seconds > 60 * 60:
            return (
                f"через: {format_number(hours, 'часов', 'час', 'часа')} "
                f"{format_number(minutes, 'минут', 'минута', 'минуты')} "
                f"{format_number(seconds, 'секунд', 'секунда', 'секунды')}"
            )
        elif dt.seconds > 60:
            return (
                f"через: {format_number(minutes, 'минут', 'минута', 'минуты')} "
                f"{format_number(seconds, 'секунд', 'секунда', 'секунды')}"
            )
        else:
            return f"через: {format_number(seconds, 'секунд', 'секунда', 'секунды')}"


def unique(ar: list) -> list:
    return list(set(ar))


def get_text(message: Message) -> str:
    return message.text or message.caption or ""
