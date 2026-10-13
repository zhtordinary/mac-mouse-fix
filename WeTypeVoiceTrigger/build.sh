#!/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PATH="/Applications/WeTypeVoiceTrigger.app"
CONTENTS_PATH="${APP_PATH}/Contents"
MACOS_PATH="${CONTENTS_PATH}/MacOS"
RESOURCES_PATH="${CONTENTS_PATH}/Resources"

echo "=== Building WeTypeVoiceTrigger ==="
mkdir -p "${MACOS_PATH}" "${RESOURCES_PATH}"

# Write Info.plist
cat << 'PLIST' > "${CONTENTS_PATH}/Info.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>
    <string>com.zibuyu.WeTypeVoiceTrigger</string>
    <key>CFBundleName</key>
    <string>WeTypeVoiceTrigger</string>
    <key>CFBundleDisplayName</key>
    <string>微信语音双击助手</string>
    <key>CFBundleExecutable</key>
    <string>WeTypeVoiceTrigger</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>2.0</string>
    <key>CFBundleVersion</key>
    <string>2</string>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
PLIST

# Compile Release Binary
swiftc -O "${DIR}/main.swift" -o "${MACOS_PATH}/WeTypeVoiceTrigger"
chmod +x "${MACOS_PATH}/WeTypeVoiceTrigger"

# Codesign Ad-Hoc
codesign --force --deep --sign - "${APP_PATH}"

echo "=== Local Build & Installation Complete: ${APP_PATH} ==="

# Optional sync to MacBook Air if reachable
AIR_HOST="haitao@100.104.233.91"
if ssh -o BatchMode=yes -o ConnectTimeout=2 "${AIR_HOST}" "true" 2>/dev/null; then
    echo "=== Syncing to MacBook Air (${AIR_HOST}) ==="
    rsync -avz --delete "${APP_PATH}/" "${AIR_HOST}:${APP_PATH}/"
    ssh "${AIR_HOST}" "codesign --force --deep --sign - '${APP_PATH}'"
    echo "=== Synced to MacBook Air successfully! ==="
else
    echo "=== Note: MacBook Air not reachable or offline, skipped remote sync. ==="
fi
