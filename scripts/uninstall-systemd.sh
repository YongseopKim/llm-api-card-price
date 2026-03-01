#!/bin/bash
set -euo pipefail

systemctl --user disable --now llm-pricing-updater.timer 2>/dev/null || true
rm -f "${HOME}/.config/systemd/user/llm-pricing-updater.service"
rm -f "${HOME}/.config/systemd/user/llm-pricing-updater.timer"
systemctl --user daemon-reload

echo "Uninstalled llm-pricing-updater"
