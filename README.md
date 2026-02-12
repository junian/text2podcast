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

See `build_instructions.md` for packaging as a standalone .app and DMG installer.
