#!/bin/bash
set -e

# Check root privileges
if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run as root"
  exit 1
fi

# Detect OS
if [ ! -f /etc/os-release ]; then
  echo "Error: This script is designed for Ubuntu/Debian systems only"
  exit 1
fi

# Update system and install dependencies
apt update && apt install -y python3 python3-pip git curl systemd

# Create project directory
mkdir -p /opt/filex
cd /opt/filex || exit

# Get requirements file
if [ ! -f requirements.txt ]; then
  curl -sSL https://raw.githubusercontent.com/AmirAfsa2006/FileX/main/requirements.txt > requirements.txt
fi

# Install Python virtual environment and dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file if it doesn't exist, prompting for required values
if [ ! -f .env ]; then
  # Provide defaults for optional values
  : "${TG_BOT_TOKEN:=}"
  : "${API_ID:=}"
  : "${API_HASH:=}"
  : "${OWNER_ID:=}"
  : "${CHANNEL_ID:=}"
  : "${DATABASE_URL:=}"
  : "${FORCE_SUB_CHANNEL:=0}"
  : "${JOIN_REQUEST_ENABLE:=false}"
  : "${START_PIC:=}"
  : "${START_MSG:=}"
  : "${ADMINS:=}"
  : "${AUTO_DELETE_TIME:=0}"
  : "${DISABLE_CHANNEL_BUTTON:=false}"

  echo "Please provide required credentials:"
  read -rp "TG_BOT_TOKEN: " TG_BOT_TOKEN
  read -rp "API_ID: " API_ID
  read -rp "API_HASH: " API_HASH
  read -rp "OWNER_ID: " OWNER_ID
  read -rp "CHANNEL_ID (negative integer): " CHANNEL_ID
  read -rp "DATABASE_URL: " DATABASE_URL
  read -rp "FORCE_SUB_CHANNEL (optional, default 0): " FORCE_SUB_CHANNEL

  cat <<EOF > .env
TG_BOT_TOKEN="${TG_BOT_TOKEN}"
API_ID="${API_ID}"
API_HASH="${API_HASH}"
OWNER_ID="${OWNER_ID}"
CHANNEL_ID="${CHANNEL_ID}"
DATABASE_URL="${DATABASE_URL}"
FORCE_SUB_CHANNEL="${FORCE_SUB_CHANNEL}"
JOIN_REQUEST_ENABLE="${JOIN_REQUEST_ENABLE}"
START_PIC="${START_PIC}"
START_MSG="${START_MSG}"
ADMINS="${ADMINS}"
AUTO_DELETE_TIME="${AUTO_DELETE_TIME}"
DISABLE_CHANNEL_BUTTON="${DISABLE_CHANNEL_BUTTON}"
EOF
  echo "Credentials saved to .env"
fi

# Set up systemd service
cat <<EOF > /etc/systemd/system/filex.service
[Unit]
Description=FileX Bot Service
After=network.target

[Service]
User=root
WorkingDirectory=/opt/filex
ExecStart=/opt/filex/venv/bin/python /opt/filex/main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable filex
systemctl start filex

# Install CLI tool
cat <<'EOF' > /usr/local/bin/FileX
#!/bin/bash
set -e
case "$1" in
  start)
    systemctl start filex
    echo "FileX service started."
    ;;
  stop)
    systemctl stop filex
    echo "FileX service stopped."
    ;;
  restart)
    systemctl restart filex
    echo "FileX service restarted."
    ;;
  status)
    systemctl status filex
    ;;
  logs)
    journalctl -u filex -f
    ;;
  config)
    nano /opt/filex/.env
    systemctl restart filex
    echo "FileX configuration updated and service restarted."
    ;;
  update)
    git -C /opt/filex pull
    source /opt/filex/venv/bin/activate
    pip install -r /opt/filex/requirements.txt
    systemctl restart filex
    echo "FileX updated and service restarted."
    ;;
  uninstall)
    systemctl stop filex
    systemctl disable filex
    rm -rf /etc/systemd/system/filex.service
    rm -rf /opt/filex
    rm -f /usr/local/bin/FileX
    echo "FileX uninstalled."
    ;;
  *)
    echo "FileX - Telegram File Sharing Bot Management"
    echo "------------------------------------------"
    echo "Usage:"
    echo "  start      - Start the bot service"
    echo "  stop       - Stop the bot service"
    echo "  restart    - Restart the bot service"
    echo "  status     - Show service status"
    echo "  logs       - Stream live logs"
    echo "  config     - Edit .env credentials"
    echo "  update     - Pull latest changes and update dependencies"
    echo "  uninstall  - Remove service and clean up"
    echo ""
    echo "If no argument is provided, the menu is displayed:"
    echo "  $0"
    echo "      1) start"
    echo "      2) stop"
    echo "      3) restart"
    echo "      4) status"
    echo "      5) logs"
    echo "      6) config"
    echo "      7) update"
    echo "      8) uninstall"
    ;;
esac
EOF
chmod +x /usr/local/bin/FileX