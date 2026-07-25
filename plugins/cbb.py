"""Inline callback handlers for FileX."""

from __future__ import annotations

from pyrogram import __version__
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from bot import Bot
from config import OWNER_ID


@Bot.on_callback_query()
async def callback_handler(client: Bot, query: CallbackQuery):
    if query.data == "about":
        await query.answer()
        await query.message.edit_text(
            (
                "<b>FileX</b>\n\n"
                f"Owner: <a href='tg://user?id={OWNER_ID}'>Contact owner</a>\n"
                "Language: <code>Python 3</code>\n"
                f"Framework: <a href='https://pyrofork.wulan17.dev/'>"
                f"Pyrofork {__version__}</a>\n"
                "Source: <a href='https://github.com/AmirAfsa2006/FileX'>"
                "GitHub repository</a>"
            ),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Close", callback_data="close")]]
            ),
        )
    elif query.data == "close":
        await query.answer()
        reply_to = query.message.reply_to_message
        await query.message.delete()
        if reply_to:
            try:
                await reply_to.delete()
            except Exception:
                pass
    else:
        await query.answer("Unknown action", show_alert=False)