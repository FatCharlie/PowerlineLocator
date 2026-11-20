#!/usr/bin/env bash
# lockdown.sh: make the Pi's SD card read-only (or writable again).
#
# A tool that gets lent out will have its battery pulled while it's running,
# and that's how SD cards get corrupted. With the overlay file system on,
# nothing is ever written to the card: changes live in RAM and vanish at the
# next boot. So calibrate FIRST, then lock.
#
#   ./lockdown.sh on       # read-only from the next boot
#   ./lockdown.sh off      # writable from the next boot (to recalibrate or update)
#   ./lockdown.sh status
set -euo pipefail

case "${1:-status}" in
    on)
        if [ ! -f "$(dirname "$0")/cal.json" ]; then
            echo "No cal.json yet. Run calibrate.py first, or the calibration you do" >&2
            echo "afterwards will be lost at every reboot." >&2
            exit 1
        fi
        sudo raspi-config nonint do_overlayfs 0
        echo "Read-only from the next boot. sudo reboot"
        ;;
    off)
        sudo raspi-config nonint do_overlayfs 1
        echo "Writable from the next boot. sudo reboot"
        ;;
    status)
        if grep -q "boot=overlay" /proc/cmdline 2>/dev/null; then
            echo "Locked: read-only overlay is active."
        else
            echo "Unlocked: the SD card is writable."
        fi
        ;;
    *)
        echo "usage: $0 on|off|status" >&2
        exit 2
        ;;
esac
