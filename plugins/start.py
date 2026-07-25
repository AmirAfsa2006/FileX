"""Start-link delivery, force subscription, user stats, and broadcasting."""

from __future__ import annotations

import asyncio
import logging

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot import Bot
from config import (
    ADMINS,
    AUTO_DELETE_MSG,
    AUTO_DELETE_TIME,
    CUSTOM_CAPTION,
    DISABLE_CHANNEL_BUTTON,
    FORCE_MSG,
    FORCE_SUB_CHANNEL,
    JOIN_REQUEST_ENABLE,
    PROTECT_CONTENT,
    START_MSG,
    START_PIC,
)
from database.database import add_user, del_user, full_userbase, present_user
from helper_func import decode, delete_file, get_messages, get_payload_ids, subscribed

logger = logging.getLogger(__name__)
WAIT_MSG = "<b>Processing…</b>"
REPLY_ERROR = "<code>Reply to a Telegram message with /broadcast.</code>"


def _user_format(message: Message) -> dict:
    user = message.from_user
    return {
        "first": user.first_name or "",
        "last": user.last_name or "",
        "username": f"@{user.username}" if user.username else "",
        "mention": user.mention,
        "id": user.id,
    }


async def _copy_with_retry(message, **kwargs):
    while True:
        try:
            return await message.copy(**kwargs)
        except FloodWait as exc:
            await asyncio.sleep(exc.value)


@Bot.on_message(filters.command("start") & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    if not await present_user(user_id):
        await add_user(user_id)

    if len(message.command) > 1:
        try:
            payload = await decode(message.command[1])
            message_ids = get_payload_ids(payload, client.db_channel.id)
        except (ValueError, UnicodeError):
            await message.reply_text("This FileX link is invalid or expired.", quote=True)
            return

        progress = await message.reply_text("Please wait…", quote=True)
        try:
            stored_messages = await get_messages(client, message_ids)
        except Exception:
            logger.exception("Failed to retrieve start-link messages")
            await progress.edit_text("Something went wrong while retrieving the file.")
            return

        await progress.delete()
        delivered = []
        for stored in stored_messages:
            caption = stored.caption.html if stored.caption else ""
            if CUSTOM_CAPTION and stored.document:
                try:
                    caption = CUSTOM_CAPTION.format(
                        previouscaption=caption,
                        filename=stored.document.file_name or "",
                    )
                except (KeyError, ValueError):
                    logger.warning("CUSTOM_CAPTION has invalid placeholders")
            reply_markup = stored.reply_markup if DISABLE_CHANNEL_BUTTON else None
            try:
                copied = await _copy_with_retry(
                    stored,
                    chat_id=user_id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                    protect_content=PROTECT_CONTENT,
                )
                if AUTO_DELETE_TIME:
                    delivered.append(copied)
                await asyncio.sleep(0.25)
            except Exception:
                logger.exception("Failed to deliver database message %s", stored.id)

        if AUTO_DELETE_TIME and delivered:
            notice = await client.send_message(
                user_id,
                AUTO_DELETE_MSG.format(time=AUTO_DELETE_TIME),
            )
            asyncio.create_task(delete_file(delivered, client, notice))
        return

    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("About FileX", callback_data="about"),
            InlineKeyboardButton("Close", callback_data="close"),
        ]]
    )
    text = START_MSG.format(**_user_format(message))
    if START_PIC:
        await message.reply_photo(START_PIC, caption=text, reply_markup=keyboard, quote=True)
    else:
        await message.reply_text(
            text,
            reply_markup=keyboard,
            disable_web_page_preview=True,
            quote=True,
        )


@Bot.on_message(filters.command("start") & filters.private)
async def not_joined(client: Client, message: Message):
    if not FORCE_SUB_CHANNEL:
        return

    if JOIN_REQUEST_ENABLE:
        invite = await client.create_chat_invite_link(
            FORCE_SUB_CHANNEL,
            creates_join_request=True,
        )
        button_url = invite.invite_link
    else:
        button_url = client.invitelink

    buttons = [[InlineKeyboardButton("Join Channel", url=button_url)]]
    if len(message.command) > 1:
        buttons.append(
            [
                InlineKeyboardButton(
                    "Try Again",
                    url=f"https://t.me/{client.username}?start={message.command[1]}",
                )
            ]
        )

    await message.reply_text(
        FORCE_MSG.format(**_user_format(message)),
        reply_markup=InlineKeyboardMarkup(buttons),
        quote=True,
        disable_web_page_preview=True,
    )


@Bot.on_message(filters.command("users") & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    progress = await message.reply_text(WAIT_MSG)
    users = await full_userbase()
    await progress.edit_text(f"<b>{len(users)}</b> users are using FileX.")


@Bot.on_message(
    filters.command("broadcast") & filters.private & filters.user(ADMINS)
)
async def broadcast(client: Bot, message: Message):
    if not message.reply_to_message:
        notice = await message.reply_text(REPLY_ERROR)
        await asyncio.sleep(8)
        await notice.delete()
        return

    users = await full_userbase()
    progress = await message.reply_text("<i>Broadcasting…</i>")
    successful = blocked = deleted = unsuccessful = 0

    for chat_id in users:
        try:
            await _copy_with_retry(message.reply_to_message, chat_id=chat_id)
            successful += 1
        except UserIsBlocked:
            await del_user(chat_id)
            blocked += 1
        except InputUserDeactivated:
            await del_user(chat_id)
            deleted += 1
        except Exception:
            unsuccessful += 1

    await progress.edit_text(
        "<b><u>Broadcast completed</u>\n\n"
        f"Total users: <code>{len(users)}</code>\n"
        f"Successful: <code>{successful}</code>\n"
        f"Blocked: <code>{blocked}</code>\n"
        f"Deleted accounts: <code>{deleted}</code>\n"
        f"Unsuccessful: <code>{unsuccessful}</code></b>"
    )