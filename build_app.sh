#!/bin/bash
set -e

# Load environment variables
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Copy .env.example to .env and fill in your credentials"
    exit 1
fi

# Load .env file properly (handle quoted values)
set -a
source .env
set +a

# Validate required variables
if [ -z "$DEVELOPER_ID_APPLICATION" ] || [ -z "$APPLE_ID" ] || [ -z "$APPLE_TEAM_ID" ] || [ -z "$APPLE_APP_SPECIFIC_PASSWORD" ] || [ -z "$APP_BUNDLE_ID" ]; then
    echo "Error: Missing required environment variables in .env"
    echo "Please check .env.example for required variables"
    exit 1
fi

APP_PATH="dist/$APP_NAME.app"
DMG_FILE="dist/$APP_NAME.dmg"

echo "Building $APP_NAME macOS App..."

# Unset VIRTUAL_ENV to avoid mismatch warnings and ensure uv uses the project environment
unset VIRTUAL_ENV

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Install from https://docs.astral.sh/uv/"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
uv sync

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist *.spec

# Build the app
echo "Building app bundle..."
uv run pyinstaller \
  --name="$APP_NAME" \
  --windowed \
  --onedir \
  --clean \
  main.py

rm -rf build/
rm -rf dist/$APP_NAME/

echo ""
echo "✓ Build complete!"
echo "App location: $APP_PATH"

echo "=== Code Signing and Notarization Process ==="
echo ""

# Check if app exists
if [ ! -d "$APP_PATH" ]; then
    echo "Error: App not found at $APP_PATH"
    exit 1
fi

# Step 1: Sign the app bundle
echo "Step 1: Signing app bundle..."
codesign --force --deep --sign "$DEVELOPER_ID_APPLICATION" \
    --options runtime \
    --entitlements entitlements.plist \
    --timestamp \
    "$APP_PATH"

# Verify signature
echo "Verifying app signature..."
codesign --verify --verbose "$APP_PATH"
spctl --assess --verbose "$APP_PATH"

echo "✓ App signed successfully"
echo ""

# Step 2: Create DMG
echo "Step 2: Creating DMG..."
if [ -f "$DMG_FILE" ]; then
    rm "$DMG_FILE"
fi

npx -y create-dmg@7 "$APP_PATH" dist --no-version-in-filename --dmg-title "$APP_NAME"

echo "✓ DMG created"
echo ""

# Step 3: Sign the DMG
# echo "Step 3: Signing DMG..."
# codesign --force --sign "$DEVELOPER_ID_APPLICATION" \
#     --timestamp \
#     "$DMG_FILE"

# Verify DMG signature
echo "Verifying DMG signature..."
codesign --verify --verbose "$DMG_FILE"

echo "✓ DMG signed successfully"
echo ""

# Step 4: Notarize the DMG
echo "Step 4: Submitting DMG for notarization..."
echo "This may take several minutes..."

xcrun notarytool submit "$DMG_FILE" \
    --apple-id "$APPLE_ID" \
    --team-id "$APPLE_TEAM_ID" \
    --password "$APPLE_APP_SPECIFIC_PASSWORD" \
    --wait

echo "✓ Notarization complete"
echo ""

# Step 5: Staple the notarization ticket
echo "Step 5: Stapling notarization ticket to DMG..."
xcrun stapler staple "$DMG_FILE"

# Verify stapling
echo "Verifying stapled ticket..."
xcrun stapler validate "$DMG_FILE"

echo ""
echo "=== SUCCESS ==="
echo "✓ $DMG_FILE is signed, notarized, and stapled"
echo "✓ Ready for distribution"
echo ""
echo "You can verify with:"
echo "  spctl --assess --type open --context context:primary-signature -v $DMG_FILE"
