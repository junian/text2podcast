#!/bin/bash
set -e

echo "Building Text2Podcast macOS App..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Install from https://docs.astral.sh/uv/"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
uv sync

# Install build tools
echo "Installing PyInstaller..."
uv pip install pyinstaller

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist *.spec

# Build the app
echo "Building app bundle..."
uv run pyinstaller --name="Text2Podcast" \
  --windowed \
  --onedir \
  --hidden-import=elevenlabs \
  --hidden-import=pydub \
  --hidden-import=nicegui \
  --collect-all nicegui \
  main.py

echo ""
echo "✓ Build complete!"
echo "App location: dist/Text2Podcast.app"
echo ""
echo "To test the app:"
echo "  open dist/Text2Podcast.app"
echo ""
echo "To create DMG installer:"
echo "  1. Install create-dmg: brew install create-dmg"
echo "  2. Run: ./create_dmg.sh"
