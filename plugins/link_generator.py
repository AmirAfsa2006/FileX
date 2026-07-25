"""Interactive single-file and batch deep-link generation."""

from __future__ import annotations

from urllib.parse import quote

from pyrogram import Client, filters
from pyrogram.errors import ListenerTimeout
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot import Bot
from config import ADMINS
from helper_func import encode, get_message_id

MESSAGE_FILTER = filters.forwarded | (filters.text & ~filters.forwarded)


def _share_markup(link: str) -> InlineKeyboardMarkup:
    share_url = f"https://t.me/share/url?url={quote(link, safe='')}"
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Share URL", url=share_url)]]
    )


async def _ask_for_db_message(
    client: Client,
    chat_id: int,
    prompt: str,
) -> tuple[Message, int] | None:
    while True:
        try:
            response = await client.ask(
                chat_id,
                prompt,
                filters=MESSAGE_FILTER,
                timeout=60,
            )
        except ListenerTimeout:
            return None
        message_id = await get_message_id(client, response)
        if message_id:
            return response, message_id
        await response.reply_text(
            "That message or link is not from the configured database channel.",
            quote=True,
        )


@Bot.on_message(filters.command("batch") & filters.private & filters.user(ADMINS))
async def batch(client: Client, message: Message):
    first = await _ask_for_db_message(
        client,
        message.from_user.id,
        "Forward the first database-channel message, or send its post link.",
    )
    if first is None:
        return

    last = await _ask_for_db_message(
        client,
        message.from_user.id,
        "Forward the last database-channel message, or send its post link.",
    )
    if last is None:
        return

    response, last_id = last
    payload = (
        f"get-{first[1] * abs(client.db_channel.id)}"
        f"-{last_id * abs(client.db_channel.id)}"
    )
    link = f"https://t.me/{client.username}?start={await encode(payload)}"
    await response.reply_text(
        f"<b>Here is your batch link</b>\n\n{link}",
        quote=True,
        reply_markup=_share_markup(link),
    )


@Bot.on_message(filters.command("genlink") & filters.private & filters.user(ADMINS))
async def link_generator(client: Client, message: Message):
    result = await _ask_for_db_message(
        client,
        message.from_user.id,
        "Forward a database-channel message, or send its post link.",
    )
    if result is None:
        return

    response, message_id = result
    payload = f"get-{message_id * abs(client.db_channel.id)}"
    link = f"https://t.me/{client.username}?start={await encode(payload)}"
    await response.reply_text(
        f"<b>Here is your link</b>\n\n{link}",
        quote=True,
        reply_markup=_share_markup(link),
    )