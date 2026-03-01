#!/bin/bash
set -euo pipefail

REPO_PATH="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_DIR="${HOME}/.config/systemd/user"

mkdir -p "${SERVICE_DIR}"
mkdir -p "${REPO_PATH}/logs"

sed "s|__REPO_PATH__|${REPO_PATH}|g" "${REPO_PATH}/scripts/llm-pricing-updater.service" > "${SERVICE_DIR}/llm-pricing-updater.service"
sed "s|__REPO_PATH__|${REPO_PATH}|g" "${REPO_PATH}/scripts/llm-pricing-updater.timer" > "${SERVICE_DIR}/llm-pricing-updater.timer"

systemctl --user daemon-reload
systemctl --user enable --now llm-pricing-updater.timer

echo "Installed and enabled llm-pricing-updater.timer"
echo "Check status: systemctl --user status llm-pricing-updater.timer"
