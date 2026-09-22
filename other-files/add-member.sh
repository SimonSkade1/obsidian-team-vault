#!/usr/bin/env bash
# Add one member device to this automation host's Syncthing and share the vault
# folder with it — the host half of INSTALL_AND_SETUP.md steps 2 and 5 (VPS_SETUP_INFO.md step 3.4).
# Hub and spoke: only this machine shares the folder, members never with each other.
#
#   other-files/add-member.sh <DEVICE-ID> <name>   add a member and share
#   other-files/add-member.sh                      show who the folder is shared with
#
# Runs against the Syncthing on this machine over its local REST API (no GUI, no
# ssh tunnel needed). Needs python3 and curl. Override with VAULT_FOLDER_ID (folder
# id, default team-vault) or STHOME (the directory holding config.xml).
set -euo pipefail

FOLDER_ID="${VAULT_FOLDER_ID:-team-vault}"

cfg=""
if [ -n "${STHOME:-}" ]; then
	cfg="$STHOME/config.xml"
else
	for c in "$HOME/.local/state/syncthing/config.xml" \
		"$HOME/.config/syncthing/config.xml" \
		"$HOME/Library/Application Support/Syncthing/config.xml"; do
		[ -f "$c" ] && { cfg="$c"; break; }
	done
fi
[ -f "$cfg" ] || { echo "no Syncthing config.xml found — set STHOME to its directory" >&2; exit 1; }

eval "$(python3 - "$cfg" <<'PY'
import sys, xml.etree.ElementTree as ET
gui = ET.parse(sys.argv[1]).getroot().find("gui")
port = gui.find("address").text.rsplit(":", 1)[1]
print('APIKEY=%s' % gui.find("apikey").text)
print('BASE=http://127.0.0.1:%s' % port)
PY
)"
api() { curl -sS --fail-with-body -H "X-API-Key: $APIKEY" "$@"; }

folder="$(api "$BASE/rest/config/folders/$FOLDER_ID" 2>/dev/null)" || {
	echo "this Syncthing has no folder '$FOLDER_ID' — is this the automation host? (VPS_SETUP_INFO.md step 3)" >&2; exit 1; }

if [ $# -eq 0 ]; then
	echo "folder $FOLDER_ID is shared with:"
	python3 -c 'import json,sys;[print(" ",d["deviceID"]) for d in json.loads(sys.argv[1])["devices"]]' "$folder"
	echo "this host's own device ID: $(api "$BASE/rest/system/status" | python3 -c 'import json,sys;print(json.load(sys.stdin)["myID"])')"
	exit 0
fi
[ $# -eq 2 ] || { sed -n '2,8p' "$0"; exit 2; }

id="$(printf '%s' "$1" | tr -d '[:space:]' | tr '[:lower:]' '[:upper:]')"
[ "${#id}" -eq 63 ] || [ "${#id}" -eq 56 ] || { echo "'$1' is not a Syncthing device ID (63 characters with dashes)" >&2; exit 2; }
name="$2"

if api "$BASE/rest/config/devices" | grep -qF "$id"; then
	echo "device already known: $name"
else
	api -X POST -d "{\"deviceID\":\"$id\",\"name\":\"$name\"}" "$BASE/rest/config/devices" >/dev/null
	echo "added device $name"
fi

if printf '%s' "$folder" | grep -qF "$id"; then
	echo "already shared with $name — nothing to do"
else
	devices="$(python3 -c 'import json,sys;d=json.loads(sys.argv[1])["devices"];d.append({"deviceID":sys.argv[2]});print(json.dumps({"devices":d}))' "$folder" "$id")"
	api -X PATCH -d "$devices" "$BASE/rest/config/folders/$FOLDER_ID" >/dev/null
	echo "shared $FOLDER_ID with $name"
fi

me="$(api "$BASE/rest/system/status" | python3 -c 'import json,sys;print(json.load(sys.stdin)["myID"])')"
myname="$(api "$BASE/rest/config/devices" | python3 -c 'import json,sys;print(next(d["name"] for d in json.load(sys.stdin) if d["deviceID"]==sys.argv[1]))' "$me")"
echo
echo "Tell $name: a device notification ($myname wants to connect) appears at the top of"
echo "their Syncthing; the folder notification follows only once they have accepted the"
echo "device. Accept both, pick a local path, then continue with INSTALL_AND_SETUP.md step 6 (tell"
echo "Claude to complete the setup)."
