"""Shared encoding, subscription, Telegram, and timing helpers."""

from __future__ import annotations

import asyncio
import base64
import logging
import re
from collections.abc import Iterable

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import FloodWait, UserNotParticipant

from config import (
    ADMINS,
    AUTO_DELETE_TIME,
    AUTO_DEL_SUCCESS_MSG,
    FORCE_SUB_CHANNEL,
)

logger = logging.getLogger(__name__)
POST_LINK_RE = re.compile(
    r"^https?://(?:www\.)?t(?:elegram)?\.me/(?:c/)?([^/?#]+)/(\d+)(?:[/?#].*)?$",
    re.IGNORECASE,
)


async def is_subscribed(_, client, update) -> bool:
    """Return whether an update sender may use force-sub protected handlers."""
    if not FORCE_SUB_CHANNEL:
        return True

    user = getattr(update, "from_user", None)
    if user is None:
        return False
    if user.id in ADMINS:
        return True

    try:
        member = await client.get_chat_member(FORCE_SUB_CHANNEL, user.id)
    except UserNotParticipant:
        return False
    except Exception:
        logger.exception("Could not check force-sub membership for user %s", user.id)
        return False

    return member.status in {
        ChatMemberStatus.OWNER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.MEMBER,
    }


async def encode(value: str) -> str:
    """Encode a start-link payload using URL-safe Base64 without padding."""
    return base64.urlsafe_b64encode(value.encode("ascii")).decode("ascii").rstrip("=")


async def decode(value: str) -> str:
    """Decode current and legacy padded URL-safe Base64 payloads."""
    value = value.strip().strip("=")
    padded = value + ("=" * (-len(value) % 4))
    return base64.urlsafe_b64decode(padded.encode("ascii")).decode("ascii")


def get_payload_ids(payload: str, channel_id: int) -> list[int]:
    """Validate a FileX start payload and return its message IDs."""
    parts = payload.split("-")
    if parts[0] != "get" or len(parts) not in {2, 3}:
        raise ValueError("Invalid FileX payload")

    divisor = abs(channel_id)
    if divisor == 0:
        raise ValueError("Database channel ID is not configured")

    decoded = []
    for raw_value in parts[1:]:
        value = int(raw_value)
        if value % divisor:
            raise ValueError("Payload does not belong to this database channel")
        decoded.append(value // divisor)

    if len(decoded) == 1:
        return decoded

    step = 1 if decoded[0] <= decoded[1] else -1
    return list(range(decoded[0], decoded[1] + step, step))


async def get_messages(client, message_ids: Iterable[int]) -> list:
    """Fetch database-channel messages in API-safe chunks."""
    ids = list(message_ids)
    messages: list = []

    for offset in range(0, len(ids), 200):
        chunk = ids[offset : offset + 200]
        while True:
            try:
                result = await client.get_messages(client.db_channel.id, chunk)
                break
            except FloodWait as exc:
                await asyncio.sleep(exc.value)

        if not isinstance(result, list):
            result = [result]
        messages.extend(message for message in result if message and not message.empty)

    return messages


async def get_message_id(client, message) -> int:
    """Extract and validate a database-channel message ID."""
    forward_chat = getattr(message, "forward_from_chat", None)
    forward_id = getattr(message, "forward_from_message_id", None)
    if forward_chat is not None:
        if forward_chat.id == client.db_channel.id and forward_id:
            return int(forward_id)
        return 0

    # Pyrofork exposes newer Telegram forward metadata as ``forward_origin``.
    origin = getattr(message, "forward_origin", None)
    origin_chat = getattr(origin, "chat", None)
    origin_message_id = getattr(origin, "message_id", None)
    if origin_chat is not None:
        if origin_chat.id == client.db_channel.id and origin_message_id:
            return int(origin_message_id)
        return 0

    if getattr(message, "forward_sender_name", None):
        return 0

    text = (getattr(message, "text", None) or "").strip()
    match = POST_LINK_RE.match(text)
    if not match:
        return 0

    channel_ref, raw_message_id = match.groups()
    expected_id = str(client.db_channel.id)
    if channel_ref.isdigit():
        if f"-100{channel_ref}" != expected_id:
            return 0
    elif not client.db_channel.username or (
        channel_ref.casefold() != client.db_channel.username.casefold()
    ):
        return 0

    return int(raw_message_id)


def get_readable_time(seconds: int) -> str:
    """Format a duration as a compact day/hour/minute/second string."""
    seconds = max(0, int(seconds))
    days, seconds = divmod(seconds, 86_400)
    hours, seconds = divmod(seconds, 3_600)
    minutes, seconds = divmod(seconds, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return ":".join(parts)


async def delete_file(messages: Iterable, client, process) -> None:
    """Delete delivered copies after the configured auto-delete interval."""
    await asyncio.sleep(AUTO_DELETE_TIME)
    for message in messages:
        while True:
            try:
                await client.delete_messages(message.chat.id, message.id)
                break
            except FloodWait as exc:
                await asyncio.sleep(exc.value)
            except Exception:
                logger.exception("Unable to auto-delete message %s", message.id)
                break

    try:
        await process.edit_text(AUTO_DEL_SUCCESS_MSG)
    except Exception:
        logger.exception("Unable to update auto-delete status message")


subscribed = filters.create(is_subscribed, name="Subscribed")