#!/bin/bash
set -e

echo "Creating DMG installer..."

# Check if app exists
if [ ! -d "dist/Text2Podcast.app" ]; then
    echo "Error: App not found. Run ./build_app.sh first"
    exit 1
fi

# Check if create-dmg is installed
if ! command -v create-dmg &> /dev/null; then
    echo "Error: create-dmg not installed. Install with: brew install create-dmg"
    exit 1
fi

# Remove old DMG if exists
rm -f Text2Podcast-Installer.dmg

# Create DMG
create-dmg \
  --volname "Text2Podcast Installer" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "Text2Podcast.app" 200 190 \
  --hide-extension "Text2Podcast.app" \
  --app-drop-link 600 185 \
  "Text2Podcast-Installer.dmg" \
  "dist/Text2Podcast.app"

echo ""
echo "✓ DMG created: Text2Podcast-Installer.dmg"
echo ""
echo "Users can now:"
echo "  1. Open the DMG"
echo "  2. Drag Text2Podcast.app to Applications"
echo "  3. Launch from Applications folder"
