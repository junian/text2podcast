# Code Signing and Notarization Guide

This guide walks you through signing and notarizing your Text2Podcast app for distribution on macOS.

## Prerequisites

### 1. Apple Developer Account
- Enroll in the [Apple Developer Program](https://developer.apple.com/programs/) ($99/year)
- You need this to get a Developer ID certificate

### 2. Developer ID Certificate
1. Go to [Apple Developer Certificates](https://developer.apple.com/account/resources/certificates/list)
2. Create a "Developer ID Application" certificate
3. Download and install it in Keychain Access
4. Note your certificate name (e.g., "Developer ID Application: John Doe (ABC123XYZ)")

### 3. App-Specific Password
1. Go to [Apple ID Account](https://appleid.apple.com/account/manage)
2. Sign in with your Apple ID
3. In the "Sign-In and Security" section, select "App-Specific Passwords"
4. Click "Generate an app-specific password"
5. Enter a label (e.g., "Text2Podcast Notarization")
6. Save the generated password (format: xxxx-xxxx-xxxx-xxxx)

### 4. Team ID
1. Go to [Apple Developer Membership](https://developer.apple.com/account/#!/membership)
2. Find your Team ID (10-character alphanumeric code)

## Configuration

### Step 1: Create .env file

```bash
cp .env.example .env
```

### Step 2: Edit .env with your credentials

```bash
# Open in your editor
nano .env
```

Fill in your information:

```bash
DEVELOPER_ID_APPLICATION="Developer ID Application: Your Name (TEAM_ID)"
APPLE_ID="your.email@example.com"
APPLE_TEAM_ID="YOUR_TEAM_ID"
APPLE_APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx"
APP_BUNDLE_ID="com.yourcompany.text2podcast"
```

### Step 3: Verify your certificate

```bash
# List available signing identities
security find-identity -v -p codesigning

# You should see your "Developer ID Application" certificate
```

## Building and Signing

### Complete Process (Automated)

```bash
# 1. Build the app
./build_app.sh

# 2. Sign and notarize
./sign_and_notarize.sh
```

The script will:
1. ✓ Sign the app bundle with hardened runtime
2. ✓ Create the DMG installer
3. ✓ Sign the DMG
4. ✓ Submit DMG for notarization
5. ✓ Wait for Apple's approval (usually 2-5 minutes)
6. ✓ Staple the notarization ticket to the DMG

### Manual Process (Step by Step)

If you prefer to run steps manually:

```bash
# 1. Build the app
./build_app.sh

# 2. Sign the app bundle
codesign --force --deep --sign "Developer ID Application: Your Name (TEAM_ID)" \
    --options runtime \
    --entitlements entitlements.plist \
    --timestamp \
    dist/Text2Podcast.app

# 3. Verify app signature
codesign --verify --verbose dist/Text2Podcast.app
spctl --assess --verbose dist/Text2Podcast.app

# 4. Create DMG
./create_dmg.sh

# 5. Sign the DMG
codesign --force --sign "Developer ID Application: Your Name (TEAM_ID)" \
    --timestamp \
    Text2Podcast-Installer.dmg

# 6. Submit for notarization
xcrun notarytool submit Text2Podcast-Installer.dmg \
    --apple-id "your.email@example.com" \
    --team-id "YOUR_TEAM_ID" \
    --password "xxxx-xxxx-xxxx-xxxx" \
    --wait

# 7. Staple the ticket
xcrun stapler staple Text2Podcast-Installer.dmg

# 8. Verify
xcrun stapler validate Text2Podcast-Installer.dmg
```

## Verification

After signing and notarization, verify your DMG:

```bash
# Check signature
codesign --verify --verbose Text2Podcast-Installer.dmg

# Check notarization
spctl --assess --type open --context context:primary-signature -v Text2Podcast-Installer.dmg

# Check stapled ticket
xcrun stapler validate Text2Podcast-Installer.dmg
```

You should see:
- "accepted" for spctl assessment
- "The validate action worked!" for stapler

## Distribution

Once signed and notarized:

1. ✓ Users can download and open the DMG without warnings
2. ✓ macOS Gatekeeper will allow installation
3. ✓ No "unidentified developer" warnings
4. ✓ App will run on macOS 10.15+ without issues

## Troubleshooting

### "No identity found" error
- Ensure your Developer ID certificate is installed in Keychain Access
- Run: `security find-identity -v -p codesigning`

### Notarization fails
- Check your Apple ID and app-specific password
- Verify your Team ID is correct
- Check notarization logs: `xcrun notarytool log <submission-id> --apple-id <email> --team-id <team-id> --password <password>`

### "Invalid entitlements" error
- Ensure entitlements.plist is present
- Check that entitlements match your app's needs

### Gatekeeper still blocks the app
- Ensure you stapled the notarization ticket
- Verify with: `xcrun stapler validate Text2Podcast-Installer.dmg`

## Security Notes

- Never commit .env to version control (it's in .gitignore)
- Keep your app-specific password secure
- Rotate app-specific passwords periodically
- The entitlements.plist grants necessary permissions for:
  - Network access (ElevenLabs API)
  - File access (scripts and audio files)
  - JIT compilation (Python runtime)

## Resources

- [Apple Notarization Guide](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [Code Signing Guide](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/Introduction/Introduction.html)
- [Hardened Runtime](https://developer.apple.com/documentation/security/hardened_runtime)
