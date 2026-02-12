#!/bin/bash

DMG_FILE="Text2Podcast-Installer.dmg"
APP_PATH="dist/Text2Podcast.app"

echo "=== Signature Verification ==="
echo ""

# Check if files exist
if [ ! -f "$DMG_FILE" ]; then
    echo "❌ DMG not found: $DMG_FILE"
    echo "Run ./create_dmg.sh first"
    exit 1
fi

if [ ! -d "$APP_PATH" ]; then
    echo "❌ App not found: $APP_PATH"
    echo "Run ./build_app.sh first"
    exit 1
fi

# Verify app signature
echo "Checking app bundle signature..."
if codesign --verify --verbose "$APP_PATH" 2>&1; then
    echo "✓ App signature valid"
else
    echo "❌ App signature invalid or not signed"
fi
echo ""

# Check app with Gatekeeper
echo "Checking app with Gatekeeper..."
if spctl --assess --verbose "$APP_PATH" 2>&1; then
    echo "✓ App accepted by Gatekeeper"
else
    echo "❌ App rejected by Gatekeeper (may need notarization)"
fi
echo ""

# Verify DMG signature
echo "Checking DMG signature..."
if codesign --verify --verbose "$DMG_FILE" 2>&1; then
    echo "✓ DMG signature valid"
else
    echo "❌ DMG signature invalid or not signed"
fi
echo ""

# Check DMG with Gatekeeper
echo "Checking DMG with Gatekeeper..."
if spctl --assess --type open --context context:primary-signature -v "$DMG_FILE" 2>&1; then
    echo "✓ DMG accepted by Gatekeeper"
else
    echo "❌ DMG rejected by Gatekeeper (may need notarization)"
fi
echo ""

# Check notarization stapling
echo "Checking notarization ticket..."
if xcrun stapler validate "$DMG_FILE" 2>&1 | grep -q "The validate action worked"; then
    echo "✓ Notarization ticket stapled"
else
    echo "❌ No notarization ticket found"
fi
echo ""

echo "=== Summary ==="
echo "For full distribution, you need:"
echo "  1. Valid code signature (codesign)"
echo "  2. Gatekeeper acceptance (spctl)"
echo "  3. Notarization ticket (stapler)"
echo ""
echo "Run ./sign_and_notarize.sh to complete all steps"
