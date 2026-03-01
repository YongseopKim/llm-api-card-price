#!/bin/bash
set -euo pipefail

REPO_PATH="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_NAME="com.llm-pricing.updater.plist"
PLIST_SRC="${REPO_PATH}/scripts/${PLIST_NAME}"
PLIST_DST="${HOME}/Library/LaunchAgents/${PLIST_NAME}"

mkdir -p "${REPO_PATH}/logs"
mkdir -p "${HOME}/Library/LaunchAgents"

sed "s|__REPO_PATH__|${REPO_PATH}|g" "${PLIST_SRC}" > "${PLIST_DST}"

launchctl unload "${PLIST_DST}" 2>/dev/null || true
launchctl load "${PLIST_DST}"

echo "Installed and loaded ${PLIST_NAME}"
echo "Logs: ${REPO_PATH}/logs/"
