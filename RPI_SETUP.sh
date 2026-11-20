#!/usr/bin/env bash
# RPI_SETUP.sh: one-time Raspberry Pi setup for PowerlineLocator.
#
#   1. turns on SPI (the screen) with raspi-config
#   2. installs every package the scripts need, from apt
#   3. adds your user to the spi, gpio and audio groups
#   4. installs a boot service so the locator starts by itself at power-on
#
# Run from the repo folder:   sudo ./RPI_SETUP.sh
# Then reboot. Add --no-service to skip step 4.
set -euo pipefail

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    echo "You need to run as root for raspi-config: sudo ./RPI_SETUP.sh" >&2
    exit 1
fi
if ! command -v raspi-config >/dev/null 2>&1; then
    echo "raspi-config not found: this script is for Raspberry Pi OS." >&2
    exit 1
fi

WANT_SERVICE=1
[ "${1:-}" = "--no-service" ] && WANT_SERVICE=0
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_USER="${SUDO_USER:-}"

PACKAGES=(
    python3-numpy       # lock-in and depth solver
    python3-alsaaudio   # 4-channel capture from the UMC404HD
    python3-spidev      # Sharp Memory LCD over SPI0
    python3-gpiozero    # buttons, buzzer, display chip select
    python3-lgpio       # gpiozero's backend on Bookworm
    python3-pil         # drawing the screen
    fonts-dejavu-core   # the screen's font
    alsa-utils          # arecord -l, for poking at the interface
    git
)

echo "==> [1/4] Enabling SPI"
raspi-config nonint do_spi 0

echo "==> [2/4] Installing packages"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y "${PACKAGES[@]}"

echo "==> [3/4] Adding your user to the spi, gpio and audio groups"
if [ -n "$TARGET_USER" ] && [ "$TARGET_USER" != "root" ]; then
    usermod -aG spi,gpio,audio "$TARGET_USER"
    echo "    added $TARGET_USER"
else
    echo "    skipped: run with sudo from your normal account to have this done for you"
fi

if [ "$WANT_SERVICE" = 1 ] && [ -n "$TARGET_USER" ] && [ "$TARGET_USER" != "root" ]; then
    echo "==> [4/4] Installing the boot service (powerline-locator)"
    cat > /etc/systemd/system/powerline-locator.service <<UNIT
[Unit]
Description=PowerlineLocator receiver
After=sound.target

[Service]
User=$TARGET_USER
WorkingDirectory=$REPO
ExecStart=/usr/bin/python3 $REPO/locate.py
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT
    systemctl daemon-reload
    systemctl enable powerline-locator.service
    echo "    enabled; it starts at the next boot"
else
    echo "==> [4/4] Boot service skipped"
fi

cat <<'DONE'

Setup finished. Reboot so SPI, the groups and the service take effect:

    sudo reboot

Then, from the repo folder, as your normal user (no sudo):

    python3 selftest.py                          # software check, no hardware needed
    sudo systemctl stop powerline-locator        # free the interface for the checks
    python3 check_hw.py --interactive            # hardware check
    python3 calibrate.py                         # once, on the calibration wire
    ./lockdown.sh on                             # make the SD card read-only for lending
DONE
