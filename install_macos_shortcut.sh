#!/bin/bash
# Creates a macOS .app bundle for launching the Portfolio GUI.
# The resulting app can be placed anywhere — Dock, Desktop, Applications, etc.

set -e

REPO_DIR="$HOME/Desktop/madison-portfolio2"
APP_NAME="Madison Portfolio"
APP_PATH="$HOME/Desktop/${APP_NAME}.app"
ICON_SRC="$REPO_DIR/rilakumma.jpg"

# --- Build .app bundle structure ---
echo "Creating ${APP_NAME}.app ..."
rm -rf "$APP_PATH"
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

# --- Launcher script (uses absolute path so it works from anywhere) ---
cat > "$APP_PATH/Contents/MacOS/launch" << 'LAUNCHER'
#!/bin/bash
osascript <<'APPLESCRIPT'
tell application "Terminal"
    activate
    set targetDir to (POSIX path of (path to home folder)) & "Desktop/madison-portfolio2"
    do script "cd " & quoted form of targetDir & " && bash run_gui.sh"
end tell
APPLESCRIPT
LAUNCHER
chmod +x "$APP_PATH/Contents/MacOS/launch"

# --- Info.plist ---
cat > "$APP_PATH/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launch</string>
    <key>CFBundleIconFile</key>
    <string>icon</string>
    <key>CFBundleIdentifier</key>
    <string>me.lunaportfolio.gui</string>
    <key>CFBundleName</key>
    <string>Madison Portfolio</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>
PLIST

# --- Convert rilakumma.jpg → .icns icon ---
echo "Converting icon ..."
ICONSET_DIR=$(mktemp -d)/icon.iconset
mkdir -p "$ICONSET_DIR"

# macOS iconset needs these exact sizes
for size in 16 32 64 128 256 512; do
    sips -z $size $size "$ICON_SRC" --out "$ICONSET_DIR/icon_${size}x${size}.png" > /dev/null 2>&1
done
# Retina variants (@2x)
for size in 16 32 128 256; do
    double=$((size * 2))
    sips -z $double $double "$ICON_SRC" --out "$ICONSET_DIR/icon_${size}x${size}@2x.png" > /dev/null 2>&1
done
# 512@2x = 1024
sips -z 1024 1024 "$ICON_SRC" --out "$ICONSET_DIR/icon_512x512@2x.png" > /dev/null 2>&1

iconutil -c icns "$ICONSET_DIR" -o "$APP_PATH/Contents/Resources/icon.icns"
rm -rf "$(dirname "$ICONSET_DIR")"

# --- Clear icon cache so Finder picks up the new icon ---
touch "$APP_PATH"

echo ""
echo "Done! '${APP_NAME}.app' is on your Desktop."
echo "You can drag it to the Dock, Applications folder, or anywhere else."
