"""FileX configuration loaded from environment variables and a local .env file."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)


def _env(*names: str, default: str = "") -> str:
    """Return the first defined environment variable from ``names``."""
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return value.strip()
    return default


def _int_env(*names: str, default: int = 0) -> int:
    value = _env(*names, default=str(default))
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{names[0]} must be an integer, got {value!r}") from exc


def _bool_env(*names: str, default: bool = False) -> bool:
    value = _env(*names, default=str(default))
    normalized = value.lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    raise ValueError(
        f"{names[0]} must be one of true/false, yes/no, on/off, or 1/0"
    )


def _admin_ids() -> list[int]:
    raw = _env("ADMINS")
    values = raw.replace(",", " ").split()
    try:
        admins = [int(value) for value in values]
    except ValueError as exc:
        raise ValueError("ADMINS must contain space- or comma-separated integers") from exc

    if OWNER_ID and OWNER_ID not in admins:
        admins.append(OWNER_ID)
    return admins


# Telegram credentials. Legacy names remain supported for existing deployments.
API_ID = _int_env("API_ID", "APP_ID")
APP_ID = API_ID
API_HASH = _env("API_HASH")
BOT_TOKEN = _env("BOT_TOKEN", "TG_BOT_TOKEN")
TG_BOT_TOKEN = BOT_TOKEN
OWNER_ID = _int_env("OWNER_ID")
CHANNEL_ID = _int_env("CHANNEL_ID")

# MongoDB.
DATABASE_URL = _env("DATABASE_URL", "DB_URI")
DB_URI = DATABASE_URL
DB_NAME = _env("DATABASE_NAME", default="filex")

# Runtime and optional feature settings.
PORT = _int_env("PORT", default=8080)
TG_BOT_WORKERS = _int_env("TG_BOT_WORKERS", default=4)
FORCE_SUB_CHANNEL = _int_env("FORCE_SUB_CHANNEL", default=0)
JOIN_REQUEST_ENABLE = _bool_env(
    "JOIN_REQUEST_ENABLED", "JOIN_REQUEST_ENABLE", default=False
)
PROTECT_CONTENT = _bool_env("PROTECT_CONTENT", default=False)
DISABLE_CHANNEL_BUTTON = _bool_env("DISABLE_CHANNEL_BUTTON", default=False)
AUTO_DELETE_TIME = max(0, _int_env("AUTO_DELETE_TIME", default=0))

START_PIC = _env("START_PIC")
START_MSG = _env(
    "START_MESSAGE",
    default=(
        "Hello {first}\n\n"
        "I can securely store files in a private channel and share them using "
        "special links."
    ),
)
FORCE_MSG = _env(
    "FORCE_SUB_MESSAGE",
    default=(
        "Hello {first}\n\n"
        "<b>You need to join the required channel or group before using FileX.</b>"
    ),
)
CUSTOM_CAPTION = _env("CUSTOM_CAPTION") or None
AUTO_DELETE_MSG = _env(
    "AUTO_DELETE_MSG",
    default=(
        "This file will be automatically deleted in {time} seconds. "
        "Save it before the timer expires."
    ),
)
AUTO_DEL_SUCCESS_MSG = _env(
    "AUTO_DEL_SUCCESS_MSG",
    default="Your file has been successfully deleted.",
)
BOT_STATS_TEXT = _env("BOT_STATS_TEXT", default="<b>BOT UPTIME</b>\n{uptime}")
USER_REPLY_TEXT = _env(
    "USER_REPLY_TEXT",
    default="Do not send messages directly; use a FileX command.",
)

ADMINS = _admin_ids()

LOG_LEVEL = _env("LOG_LEVEL", default="INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


def validate_required_config() -> None:
    """Raise a clear error when a required deployment setting is absent."""
    required = {
        "API_ID": API_ID,
        "API_HASH": API_HASH,
        "BOT_TOKEN": BOT_TOKEN,
        "OWNER_ID": OWNER_ID,
        "CHANNEL_ID": CHANNEL_ID,
        "DATABASE_URL": DATABASE_URL,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing required configuration: "
            + ", ".join(missing)
            + ". Add the values to .env or the process environment."
        )


def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)