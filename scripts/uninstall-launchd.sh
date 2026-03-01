#!/bin/bash
set -euo pipefail

PLIST_NAME="com.llm-pricing.updater.plist"
PLIST_DST="${HOME}/Library/LaunchAgents/${PLIST_NAME}"

launchctl unload "${PLIST_DST}" 2>/dev/null || true
rm -f "${PLIST_DST}"

echo "Uninstalled ${PLIST_NAME}"
