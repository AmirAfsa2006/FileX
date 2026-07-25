# FileX

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Pyrofork](https://img.shields.io/badge/Telegram-Pyrofork-2AABEE?logo=telegram&logoColor=white)](https://github.com/Mayuri-Chan/pyrofork)
[![License](https://img.shields.io/github/license/AmirAfsa2006/FileX)](LICENSE)
[![Status](https://img.shields.io/badge/status-active-success)](https://github.com/AmirAfsa2006/FileX)

A modern, self-hosted Telegram file-sharing bot built on **Pyrofork**, MongoDB, and Python 3.10+.

## About

FileX uses a private Telegram channel as its file store:

1. A file or post is sent to the configured private database channel.
2. FileX stores the Telegram message reference instead of downloading the file to disk.
3. An administrator generates a single-file or batch link.
4. FileX encodes the protected message range in a URL-safe Base64 `/start` payload.
5. When a user opens that link, the bot validates the payload and copies the stored post to the user.

This architecture avoids local file storage while retaining Telegram delivery performance. FileX also supports force subscription, join-request links, custom captions, protected content, batch links, broadcasting, and automatic deletion of delivered files.

## Quick installation

Run this command on an Ubuntu or Debian server with systemd:

```bash
curl -sSL https://raw.githubusercontent.com/AmirAfsa2006/FileX/main/install.sh | bash
```

The installer:

- verifies Ubuntu/Debian and systemd;
- installs Python, pip, venv, Git, curl, and required system packages;
- clones FileX into `/opt/FileX`;
- prompts for missing Telegram and MongoDB credentials;
- creates a protected `.env`;
- builds `venv` and installs pinned dependencies;
- installs and enables `filex.service`;
- installs the global `FileX` manager at `/usr/local/bin/FileX`.

> When using `curl | bash`, interactive prompts are read from `/dev/tty`. Values already exported in the environment are used without prompting.

### Non-interactive credentials

Required values can be supplied before installation:

```bash
export API_ID="123456"
export API_HASH="your_api_hash"
export BOT_TOKEN="123456:bot_token"
export OWNER_ID="123456789"
export CHANNEL_ID="-1001234567890"
export DATABASE_URL="mongodb://127.0.0.1:27017"
export FORCE_SUB_CHANNEL="0"

curl -sSL https://raw.githubusercontent.com/AmirAfsa2006/FileX/main/install.sh | bash
```

## FileX CLI

Running `FileX` without arguments opens a numbered interactive menu.

| Command | Description |
|---|---|
| `FileX start` | Start `filex.service`. |
| `FileX stop` | Stop `filex.service`. |
| `FileX restart` | Restart the service. |
| `FileX status` | Show systemd status plus PID, CPU, memory, uptime, and command usage. |
| `FileX logs` | Stream live logs with `journalctl -u filex.service -f`. |
| `FileX config` | Interactively update `.env` and restart FileX. |
| `FileX update` | Run a fast-forward-only `git pull`, update venv packages, and restart. |
| `FileX uninstall` | Disable the service and remove its unit and global CLI; project data and `.env` are retained. |
| `FileX help` | Display command help. |

Service-management operations use `sudo` automatically when needed.

## Environment variables

Required variables are validated when FileX starts.

| Variable | Required | Default | Description |
|---|:---:|---|---|
| `API_ID` | Yes | — | Telegram application ID from [my.telegram.org](https://my.telegram.org). Legacy alias: `APP_ID`. |
| `API_HASH` | Yes | — | Telegram application hash. |
| `BOT_TOKEN` | Yes | — | Bot token from [@BotFather](https://t.me/BotFather). Legacy alias: `TG_BOT_TOKEN`. |
| `OWNER_ID` | Yes | — | Telegram numeric user ID of the owner. Automatically included in `ADMINS`. |
| `CHANNEL_ID` | Yes | — | Private database channel ID, normally beginning with `-100`. The bot must be an administrator. |
| `DATABASE_URL` | Yes | — | MongoDB connection URI. Legacy alias: `DB_URI`. |
| `FORCE_SUB_CHANNEL` | No | `0` | Channel/group ID users must join. `0` disables force subscription. |
| `ADMINS` | No | owner only | Space- or comma-separated additional administrator IDs. |
| `DATABASE_NAME` | No | `filex` | MongoDB database name. |
| `PORT` | No | `8080` | Health-check HTTP server port. |
| `TG_BOT_WORKERS` | No | `4` | Pyrofork worker count. |
| `JOIN_REQUEST_ENABLED` | No | `false` | Create join-request invite links for force subscription. Legacy alias: `JOIN_REQUEST_ENABLE`. |
| `PROTECT_CONTENT` | No | `false` | Protect delivered messages from forwarding/saving where Telegram supports it. |
| `DISABLE_CHANNEL_BUTTON` | No | `false` | Remove source-channel inline buttons from delivered posts. |
| `AUTO_DELETE_TIME` | No | `0` | Seconds before delivered files are deleted; `0` disables deletion. |
| `CUSTOM_CAPTION` | No | empty | Caption template. Supports `{previouscaption}` and `{filename}`. |
| `START_PIC` | No | empty | URL or Telegram-compatible file reference for the start image. |
| `START_MESSAGE` | No | built in | Start text. Supports `{first}`, `{last}`, `{username}`, `{mention}`, and `{id}`. |
| `FORCE_SUB_MESSAGE` | No | built in | Force-subscription text with the same user placeholders. |
| `AUTO_DELETE_MSG` | No | built in | Auto-delete warning; supports `{time}`. |
| `AUTO_DEL_SUCCESS_MSG` | No | built in | Message shown after automatic deletion. |
| `BOT_STATS_TEXT` | No | built in | Stats text; supports `{uptime}`. |
| `USER_REPLY_TEXT` | No | built in | Reply sent for unsupported private messages. |
| `LOG_LEVEL` | No | `INFO` | Python log level written to stdout/stderr and captured by journald under systemd. |

Boolean values accept `true/false`, `yes/no`, `on/off`, or `1/0`.

Example `.env`:

```dotenv
API_ID=123456
API_HASH=your_api_hash
BOT_TOKEN=123456:your_bot_token
OWNER_ID=123456789
CHANNEL_ID=-1001234567890
DATABASE_URL=mongodb://127.0.0.1:27017
FORCE_SUB_CHANNEL=0
ADMINS=123456789
AUTO_DELETE_TIME=0
```

Never commit `.env`; it contains secrets.

## Bot commands

| Command | Access | Purpose |
|---|---|---|
| `/start` | Everyone | Open FileX or retrieve a linked file/batch. |
| `/genlink` | Admin | Generate a secure link for one database-channel post. |
| `/batch` | Admin | Generate a link for an inclusive post range. |
| `/users` | Admin | Display registered user count. |
| `/broadcast` | Admin | Broadcast the replied-to Telegram message. |
| `/stats` | Admin | Display bot uptime. |

The bot must be an administrator in both the private database channel and any force-subscription channel used for membership checks/invite links.

## Manual deployment

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/AmirAfsa2006/FileX.git
cd FileX
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env 2>/dev/null || touch .env
nano .env
```

Add at least the six required values shown above.

### 3. Run

```bash
python main.py
```

For persistent production deployment, use `install.sh`; it creates the hardened systemd service and CLI automatically.

## Docker

After creating `.env`:

```bash
docker build -t filex .
docker run --env-file .env --name filex --restart unless-stopped filex
```

## Updating an installed server

```bash
FileX update
FileX status
```

`FileX update` only accepts fast-forward Git updates, upgrades dependencies inside the existing virtual environment, and restarts the service.

## Security notes

- Keep the database channel private.
- Give the bot only the Telegram permissions it needs.
- The installer stores `.env` with mode `600`.
- Start payloads are URL-safe Base64 identifiers, not encryption. Access control still depends on the bot, private channel, and optional force subscription.
- Restrict SSH and MongoDB access on the host.

## License

FileX is distributed under the terms in [LICENSE](LICENSE).