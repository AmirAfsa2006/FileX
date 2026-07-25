#!/usr/bin/env bash
# FileX automated installer for Ubuntu and Debian.
# Usage: curl -sSL https://raw.githubusercontent.com/AmirAfsa2006/FileX/main/install.sh | bash

set -Eeuo pipefail

REPOSITORY_URL="${FILEX_REPOSITORY_URL:-https://github.com/AmirAfsa2006/FileX.git}"
INSTALL_DIR="${FILEX_DIR:-/opt/FileX}"
SERVICE_FILE="/etc/systemd/system/filex.service"
CLI_LINK="/usr/local/bin/FileX"
CLI_CONFIG="/etc/filex.conf"

colour() {
    local code="$1"
    shift
    printf '\033[%sm%s\033[0m\n' "$code" "$*"
}

info() { colour "1;36" "$*"; }
success() { colour "1;32" "$*"; }
warn() { colour "1;33" "$*"; }
fail() { colour "1;31" "$*" >&2; exit 1; }

cleanup() {
    if [[ -n "${TEMP_ENV:-}" && -f "${TEMP_ENV:-}" ]]; then
        rm -f "$TEMP_ENV"
    fi
    if [[ -n "${SERVICE_TEMP:-}" && -f "${SERVICE_TEMP:-}" ]]; then
        rm -f "$SERVICE_TEMP"
    fi
}
trap cleanup EXIT

if [[ ! -r /etc/os-release ]]; then
    fail "Cannot identify this operating system. FileX supports Ubuntu and Debian."
fi

# shellcheck disable=SC1091
source /etc/os-release
case "${ID:-}" in
    ubuntu|debian) ;;
    *)
        if [[ " ${ID_LIKE:-} " != *" debian "* ]]; then
            fail "Unsupported distribution '${PRETTY_NAME:-unknown}'. Use Ubuntu or Debian."
        fi
        ;;
esac

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
    SUDO=()
else
    command -v sudo >/dev/null 2>&1 || fail "sudo is required when not running as root."
    SUDO=(sudo)
fi

if ! command -v systemctl >/dev/null 2>&1 || [[ ! -d /run/systemd/system ]]; then
    fail "A systemd-based Ubuntu/Debian server is required."
fi

INSTALL_USER="${FILEX_USER:-${SUDO_USER:-$(id -un)}}"
if ! id "$INSTALL_USER" >/dev/null 2>&1; then
    fail "Installation user '$INSTALL_USER' does not exist."
fi
INSTALL_GROUP="$(id -gn "$INSTALL_USER")"

run_as_user() {
    if [[ "$(id -un)" == "$INSTALL_USER" ]]; then
        "$@"
    elif [[ ${EUID:-$(id -u)} -eq 0 ]]; then
        runuser -u "$INSTALL_USER" -- "$@"
    else
        sudo -u "$INSTALL_USER" -- "$@"
    fi
}

info "Installing required system packages…"
export DEBIAN_FRONTEND=noninteractive
"${SUDO[@]}" apt-get update -y
"${SUDO[@]}" apt-get install -y \
    python3 python3-pip python3-venv git curl systemd ca-certificates

if [[ -d "$INSTALL_DIR/.git" ]]; then
    info "Existing FileX checkout found; updating it…"
    run_as_user git -C "$INSTALL_DIR" pull --ff-only
elif [[ -e "$INSTALL_DIR" ]] && [[ -n "$(ls -A "$INSTALL_DIR" 2>/dev/null)" ]]; then
    fail "$INSTALL_DIR exists and is not an empty FileX Git checkout."
else
    info "Cloning FileX into $INSTALL_DIR…"
    "${SUDO[@]}" mkdir -p "$(dirname "$INSTALL_DIR")"
    "${SUDO[@]}" git clone "$REPOSITORY_URL" "$INSTALL_DIR"
fi
"${SUDO[@]}" chown -R "$INSTALL_USER:$INSTALL_GROUP" "$INSTALL_DIR"

ENV_FILE="$INSTALL_DIR/.env"
TEMP_ENV="$(mktemp)"
if [[ -f "$ENV_FILE" ]]; then
    cat "$ENV_FILE" >"$TEMP_ENV"
fi

read_env() {
    local key="$1"
    awk -F= -v key="$key" '$1 == key {sub(/^[^=]*=/, ""); value=$0} END {print value}' "$TEMP_ENV"
}

set_env() {
    local key="$1"
    local value="$2"
    local next
    next="$(mktemp)"
    awk -F= -v key="$key" '$1 != key' "$TEMP_ENV" >"$next"
    printf '%s=%s\n' "$key" "$value" >>"$next"
    mv "$next" "$TEMP_ENV"
}

prompt_setting() {
    local key="$1"
    local label="$2"
    local optional="${3:-false}"
    local default="${4:-}"
    local value="${!key:-}"
    local current prompt

    current="$(read_env "$key")"
    [[ -n "$value" ]] || value="$current"
    [[ -n "$value" ]] || value="$default"

    if [[ -n "$value" ]]; then
        set_env "$key" "$value"
        return
    fi

    if [[ ! -r /dev/tty ]]; then
        if [[ "$optional" == "true" ]]; then
            set_env "$key" "$default"
            return
        fi
        fail "$key is missing and no interactive terminal is available. Export it before running."
    fi

    prompt="$label"
    [[ "$optional" == "true" ]] && prompt+=" (optional; Enter uses $default)"
    while true; do
        read -r -p "$prompt: " value </dev/tty
        [[ -n "$value" ]] || value="$default"
        if [[ -n "$value" || "$optional" == "true" ]]; then
            set_env "$key" "$value"
            return
        fi
        warn "$label is required."
    done
}

info "Configuring Telegram and MongoDB credentials…"
prompt_setting API_ID "Telegram API ID"
prompt_setting API_HASH "Telegram API hash"
prompt_setting BOT_TOKEN "Bot token from @BotFather"
prompt_setting OWNER_ID "Owner Telegram user ID"
prompt_setting CHANNEL_ID "Private database channel ID"
prompt_setting DATABASE_URL "MongoDB connection URL"
prompt_setting FORCE_SUB_CHANNEL "Force-subscription channel ID" true "0"

"${SUDO[@]}" install \
    -o "$INSTALL_USER" -g "$INSTALL_GROUP" -m 600 \
    "$TEMP_ENV" "$ENV_FILE"

info "Creating the Python virtual environment…"
if [[ ! -x "$INSTALL_DIR/venv/bin/python" ]]; then
    run_as_user python3 -m venv "$INSTALL_DIR/venv"
fi
run_as_user "$INSTALL_DIR/venv/bin/python" -m pip install --upgrade pip wheel
run_as_user "$INSTALL_DIR/venv/bin/python" -m pip install \
    --upgrade -r "$INSTALL_DIR/requirements.txt"

info "Installing the FileX CLI…"
"${SUDO[@]}" install -o root -g root -m 755 "$INSTALL_DIR/FileX" "$CLI_LINK"
printf 'FILEX_DIR=%q\nFILEX_USER=%q\n' "$INSTALL_DIR" "$INSTALL_USER" |
    "${SUDO[@]}" tee "$CLI_CONFIG" >/dev/null
"${SUDO[@]}" chmod 644 "$CLI_CONFIG"

info "Creating filex.service…"
SERVICE_TEMP="$(mktemp)"
cat >"$SERVICE_TEMP" <<EOF
[Unit]
Description=FileX Telegram File-Sharing Bot
Documentation=https://github.com/AmirAfsa2006/FileX
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=$INSTALL_USER
Group=$INSTALL_GROUP
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py
Restart=on-failure
RestartSec=5
TimeoutStopSec=30
KillSignal=SIGINT
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ReadWritePaths=$INSTALL_DIR

[Install]
WantedBy=multi-user.target
EOF
"${SUDO[@]}" install -o root -g root -m 644 "$SERVICE_TEMP" "$SERVICE_FILE"
rm -f "$SERVICE_TEMP"

"${SUDO[@]}" systemctl daemon-reload
"${SUDO[@]}" systemctl enable --now filex.service

success "FileX installation completed."
printf '\n'
info "Useful commands:"
printf '  FileX status\n  FileX logs\n  FileX config\n  FileX restart\n'
printf '\n'
"${SUDO[@]}" systemctl status filex.service --no-pager || true