# Text to Podcast Converter

Convert two-person scripts into podcast-style MP3s using ElevenLabs API.

## Features

- Clean GUI built with NiceGUI
- Parse "Speaker A" and "Speaker B" formatted scripts
- ElevenLabs API integration with configurable voice IDs
- Dry Run mode to test without using API credits
- Automatic audio stitching with volume normalization
- Standalone macOS app

## Installation

```bash
# Install dependencies using uv
uv sync
```

The app uses soundfile for audio processing - no FFmpeg required!

## Running the App

```bash
# Run directly
uv run python main.py
```

## Script Format

Each line must follow this format:
```
Speaker A: Hello, welcome to our podcast!
Speaker B: Thanks for having me!
Speaker A: Let's dive into today's topic.
```

## Configuration

1. Click "Settings" in the app
2. Enter your ElevenLabs API key
3. Enter Voice IDs for Speaker A and Speaker B
4. Click "Save Settings"

Settings are stored in `~/.text2podcast_settings.json`

## Building macOS App

```bash
# Build the .app bundle
./build_app.sh

# Create DMG installer
./create_dmg.sh
```

## Code Signing and Notarization

For distribution outside the Mac App Store, you need to sign and notarize your app:

```bash
# 1. Configure your credentials
cp .env.example .env
# Edit .env with your Apple Developer credentials

# 2. Build, sign, and notarize
./build_app.sh
./sign_and_notarize.sh
```

See `SIGNING_GUIDE.md` for detailed instructions on:
- Getting a Developer ID certificate
- Creating app-specific passwords
- Complete signing and notarization process

The DMG will be ready to distribute!
