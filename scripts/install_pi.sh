#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: scripts/install_pi.sh pi@192.168.1.90" >&2
  exit 2
fi

target="$1"
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -f "$repo_dir/.env" ]]; then
  echo "missing .env; copy .env.example and set OPENAI_API_KEY" >&2
  exit 1
fi

ssh "$target" 'sudo install -d -o pi -g pi /opt/sipquest /var/lib/sipquest /var/lib/sipquest/recordings /var/lib/sipquest/music'

rsync -az --delete \
  --exclude .git \
  --exclude .venv \
  --exclude build \
  --exclude dist \
  --exclude .local-music \
  --exclude '*.wav' \
  --exclude '*.pcm' \
  --exclude '*.egg-info' \
  --exclude __pycache__ \
  --exclude .pytest_cache \
  "$repo_dir/" "$target:/opt/sipquest/"

ssh "$target" 'sudo chown -R pi:pi /opt/sipquest /var/lib/sipquest && chmod 600 /opt/sipquest/.env'

ssh "$target" 'sudo sh -s' <<'REMOTE'
set -eu

apt-get update
apt-get install -y alsa-utils python3-venv python3-gpiozero python3-lgpio python3-rpi-lgpio gpiod rsync

CONFIG=/boot/firmware/config.txt
BACKUP=/boot/firmware/config.txt.sipquest-box.bak
[ -f "$BACKUP" ] || cp "$CONFIG" "$BACKUP"
if ! grep -q '^dtoverlay=googlevoicehat-soundcard' "$CONFIG"; then
  cat >> "$CONFIG" <<'EOF'

# Google AIY Voice HAT
dtparam=i2c_arm=on
dtparam=i2s=on
dtoverlay=googlevoicehat-soundcard
EOF
fi

usermod -aG audio,gpio,i2c,spi,input pi

cd /opt/sipquest
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install .

install -m 0644 systemd/sipquest-box.service /etc/systemd/system/sipquest-box.service
systemctl daemon-reload
systemctl enable sipquest-box.service
systemctl restart sipquest-box.service
REMOTE

ssh "$target" 'systemctl --no-pager --full status sipquest-box.service || true'
