#!/usr/bin/env bash
# Link + enable the systemd user units directly from the vault (the vault
# copies stay the single source of truth; rerun after editing them, followed
# by `systemctl --user daemon-reload`). Linux-only — on macOS/Windows ask
# Claude to set up launchd / Task Scheduler equivalents for the wrapper scripts.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

# Nightly review pipeline (daily review + every-2nd-day vault cleanup).
# Unit names are prefixed pai-shared- so they cannot collide with the units of
# another vault built from the same template on this host.
systemctl --user link --force "$HERE/pai-shared-daily-review.service"
systemctl --user enable --now --force "$HERE/pai-shared-daily-review.timer"

systemctl --user daemon-reload
systemctl --user list-timers --no-pager | head -6

# A --user timer exists only while the user has a login session, so on a host you
# ssh into and log out of it would silently stop firing. Enabling lingering needs
# root, which this script does not ask for — so it only warns (see VPS_SETUP_INFO.md step 9).
ME="$(id -un)"
if command -v loginctl >/dev/null 2>&1 &&
   ! loginctl show-user "$ME" --property=Linger 2>/dev/null | grep -q 'Linger=yes'; then
	echo
	echo "WARNING: lingering is off for $ME — this timer runs only while you are logged in."
	echo "         On a server, run once:  sudo loginctl enable-linger $ME"
fi
