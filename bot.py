"""Pyrofork client and runtime lifecycle for FileX."""

from __future__ import annotations

from datetime import datetime, timezone

from aiohttp import web
from pyrogram import Client
from pyrogram.enums import ParseMode

from config import (
    API_HASH,
    API_ID,
    BOT_TOKEN,
    CHANNEL_ID,
    FORCE_SUB_CHANNEL,
    LOGGER,
    PORT,
    TG_BOT_WORKERS,
)
from plugins import web_server

logger = LOGGER(__name__)


class Bot(Client):
    """Telegram bot client with FileX-specific startup checks."""

    def __init__(self) -> None:
        super().__init__(
            name="FileX",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"},
            workers=TG_BOT_WORKERS,
        )
        self.LOGGER = LOGGER
        self.db_channel = None
        self.invitelink: str | None = None
        self.username = ""
        self.uptime = datetime.now(timezone.utc)
        self._web_runner: web.AppRunner | None = None

    async def start(self) -> "Bot":
        await super().start()
        me = await self.get_me()
        self.username = me.username or ""
        self.uptime = datetime.now(timezone.utc)
        self.set_parse_mode(ParseMode.HTML)

        if FORCE_SUB_CHANNEL:
            try:
                force_chat = await self.get_chat(FORCE_SUB_CHANNEL)
                self.invitelink = force_chat.invite_link
                if not self.invitelink:
                    self.invitelink = await self.export_chat_invite_link(
                        FORCE_SUB_CHANNEL
                    )
            except Exception as exc:
                await super().stop()
                raise RuntimeError(
                    "Unable to access FORCE_SUB_CHANNEL. Ensure the ID is correct "
                    "and FileX is an administrator with permission to invite users."
                ) from exc

        try:
            self.db_channel = await self.get_chat(CHANNEL_ID)
            test_message = await self.send_message(
                self.db_channel.id,
                "FileX startup check",
                disable_notification=True,
            )
            await test_message.delete()
        except Exception as exc:
            await super().stop()
            raise RuntimeError(
                "Unable to access CHANNEL_ID. Ensure FileX is an administrator "
                "in the private database channel."
            ) from exc

        self._web_runner = web.AppRunner(await web_server())
        await self._web_runner.setup()
        await web.TCPSite(self._web_runner, "0.0.0.0", PORT).start()

        logger.info(
            "FileX is running as @%s; health endpoint listening on port %s",
            self.username,
            PORT,
        )
        return self

    async def stop(self, *args) -> None:
        if self._web_runner is not None:
            await self._web_runner.cleanup()
            self._web_runner = None
        await super().stop()
        logger.info("FileX stopped")