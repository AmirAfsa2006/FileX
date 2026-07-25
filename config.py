#(©)CodeXBotz

import os
# Ensure .env loading_dotenv
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables from .env file
load_dotenv()

def _get_env(key: str, default: str = "") -> str:
    """Get environment variable with fallback to empty string."""
    return os.environ.get(key, default)

def _get_env_int(key: str, default: int = 0) -> int:
    """Get environment variable as integer with fallback."""
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default

def _get_env_bool(key: str, default: bool = False) -> bool:
    """Get environment variable as boolean."""
    val = _get_env(key, "").lower()
    if val in ("true", "1", "yes", "on"):
        return True
    elif val in ("false", "0", "no", "off"):
        return False
    return default

# Bot token @Botfather (supports both TG_BOT_TOKEN and BOT_TOKEN)
TG_BOT_TOKEN = _get_env("TG_BOT_TOKEN", _get_env("BOT_TOKEN", ""))

# Your API ID from my.telegram.org (supports both APP_ID and API_ID)
APP_ID = _get_env_int("APP_ID", _get_env_int("API_ID", 0))

# Your API Hash from my.telegram.org (supports both API_HASH and TG_API_HASH)
API_HASH = _get_env("API_HASH", _get_env("TG_API_HASH", ""))

# Your db channel Id
CHANNEL_ID = _get_env_int("CHANNEL_ID", 0)

# OWNER ID
OWNER_ID = _get_env_int("OWNER_ID", 0)

# Port
PORT = _get_env("PORT", "8080")

# Database 
DB_URI = _get_env("DATABASE_URL", "")
DB_NAME = _get_env("DATABASE_NAME", "filesharexbot")

# force sub channel id, if you want enable force sub
FORCE_SUB_CHANNEL = _get_env_int("FORCE_SUB_CHANNEL", 0)
JOIN_REQUEST_ENABLE = _get_env("JOIN_REQUEST_ENABLED", None)

TG_BOT_WORKERS = _get_env_int("TG_BOT_WORKERS", 4)

# start message
START_PIC = _get_env("START_PIC", "")
START_MSG = _get_env("START_MESSAGE", "Hello {first}\n\nI can store private files in Specified Channel and other users can access it from special link.")

try:
    ADMINS = []
    for x in (_get_env("ADMINS", "").split()):
        if x.strip():
            ADMINS.append(int(x))
except ValueError:
    raise Exception("Your Admins list does not contain valid integers.")

# Force sub message 
FORCE_MSG = _get_env("FORCE_SUB_MESSAGE", "Hello {first}\n\n<b>You need to join in my Channel/Group to use me\n\nKindly Please join Channel</b>")

# set your Custom Caption here, Keep None for Disable Custom Caption
CUSTOM_CAPTION = _get_env("CUSTOM_CAPTION", None)

# set True if you want to prevent users from forwarding files from bot
PROTECT_CONTENT = _get_env_bool("PROTECT_CONTENT", False)

# Auto delete time in seconds.
AUTO_DELETE_TIME = _get_env_int("AUTO_DELETE_TIME", 0)
AUTO_DELETE_MSG = _get_env("AUTO_DELETE_MSG", "This file will be automatically deleted in {time} seconds. Please ensure you have saved any necessary content before this time.")
AUTO_DEL_SUCCESS_MSG = _get_env("AUTO_DEL_SUCCESS_MSG", "Your file has been successfully deleted. Thank you for using our service. ✅")

# Set true if you want Disable your Channel Posts Share button
DISABLE_CHANNEL_BUTTON = _get_env_bool("DISABLE_CHANNEL_BUTTON", False)

BOT_STATS_TEXT = "<b>BOT UPTIME</b>\n{uptime}"
USER_REPLY_TEXT = "❌Don't send me messages directly I'm only File Share bot!"

ADMINS.append(OWNER_ID)
# Removed hard-coded third-party admin ID as per clean refactor

LOG_FILE_NAME = "filesharingbot.txt"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        RotatingFileHandler(
            LOG_FILE_NAME,
            maxBytes=50000000,
            backupCount=10
        ),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)