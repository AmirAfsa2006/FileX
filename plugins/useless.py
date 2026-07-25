"""Runtime statistics and fallback private-message responses."""

from __future__ import annotations

from datetime import datetime, timezone

from pyrogram import filters
from pyrogram.types import Message

from bot import Bot
from config import ADMINS, BOT_STATS_TEXT, USER_REPLY_TEXT
from helper_func import get_readable_time


@Bot.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats(bot: Bot, message: Message):
    now = datetime.now(timezone.utc)
    elapsed = int((now - bot.uptime).total_seconds())
    await message.reply_text(BOT_STATS_TEXT.format(uptime=get_readable_time(elapsed)))


@Bot.on_message(filters.private & filters.incoming, group=10)
async def fallback_reply(_, message: Message):
    if USER_REPLY_TEXT:
        await message.reply_text(USER_REPLY_TEXT)