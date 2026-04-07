import pytz
from datetime import datetime, time
from discord import ChannelType


def get_local_today_start(tz_name: str = "Europe/Stockholm") -> datetime:
    tz = pytz.timezone(tz_name)
    today = datetime.now(tz).date()
    return tz.localize(datetime.combine(today, time.min))


async def get_today_messages(channel, tz_name: str = "Europe/Stockholm") -> list:
    today_start = get_local_today_start(tz_name)
    today_start_utc = today_start.astimezone(pytz.UTC)

    messages = []
    async for message in channel.history(after=today_start_utc, limit=500):
        if message.type is not None and message.type != ChannelType.public_thread:
            if message.author.bot:
                continue
            if not message.content:
                continue
            messages.append(message)

    messages.reverse()
    return messages


def format_chat_for_llm(messages: list) -> str:
    if not messages:
        return ""

    formatted = []
    for msg in messages:
        author = msg.author.display_name
        content = msg.content
        formatted.append(f"{author}: {content}")

    return "\n".join(formatted)


def get_local_date_str(tz_name: str = "Europe/Stockholm") -> str:
    tz = pytz.timezone(tz_name)
    return datetime.now(tz).strftime("%Y-%m-%d")
