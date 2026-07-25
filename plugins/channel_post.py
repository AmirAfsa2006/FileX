"""Store private admin uploads and attach FileX links to channel posts."""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import quote

from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot import Bot
from config import ADMINS, CHANNEL_ID, DISABLE_CHANNEL_BUTTON
from helper_func import encode

logger = logging.getLogger(__name__)
ADMIN_COMMANDS = ["start", "users", "broadcast", "batch", "genlink", "stats"]


async def _link_for_message(client: Client, message_id: int) -> str:
    converted_id = message_id * abs(client.db_channel.id)
    payload = await encode(f"get-{converted_id}")
    return f"https://t.me/{client.username}?start={payload}"


def _share_markup(link: str) -> InlineKeyboardMarkup:
    url = f"https://t.me/share/url?url={quote(link, safe='')}"
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Share URL", url=url)]]
    )


async def _edit_markup_with_retry(message: Message, reply_markup) -> None:
    while True:
        try:
            await message.edit_reply_markup(reply_markup)
            return
        except FloodWait as exc:
            await asyncio.sleep(exc.value)


@Bot.on_message(
    filters.private
    & filters.user(ADMINS)
    & ~filters.command(ADMIN_COMMANDS)
)
async def channel_post(client: Client, message: Message):
    progress = await message.reply_text("Please wait…", quote=True)
    while True:
        try:
            post_message = await message.copy(
                chat_id=client.db_channel.id,
                disable_notification=True,
            )
            break
        except FloodWait as exc:
            await asyncio.sleep(exc.value)
        except Exception:
            logger.exception("Unable to copy an admin upload to the database channel")
            await progress.edit_text("Something went wrong while storing the message.")
            return

    link = await _link_for_message(client, post_message.id)
    reply_markup = _share_markup(link)
    await progress.edit_text(
        f"<b>Here is your link</b>\n\n{link}",
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )

    if not DISABLE_CHANNEL_BUTTON:
        try:
            await _edit_markup_with_retry(post_message, reply_markup)
        except Exception:
            logger.exception("Unable to add a share button to database message %s", post_message.id)


@Bot.on_message(filters.channel & filters.incoming & filters.chat(CHANNEL_ID))
async def new_post(client: Client, message: Message):
    if DISABLE_CHANNEL_BUTTON:
        return

    link = await _link_for_message(client, message.id)
    try:
        await _edit_markup_with_retry(message, _share_markup(link))
    except Exception:
        logger.exception("Unable to add a share button to channel message %s", message.id)