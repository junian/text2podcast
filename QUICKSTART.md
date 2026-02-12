# Quick Start Guide

## 1. Install Dependencies

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync

# Install FFmpeg (required for audio processing)
brew install ffmpeg
```

## 2. Run the App (Development)

```bash
uv run python main.py
```

The app will open in a native window.

## 3. Configure Settings

1. Click "Settings" in the app
2. Enter your ElevenLabs API key (get one at https://elevenlabs.io)
3. Enter Voice IDs for Speaker A and Speaker B
   - Find voice IDs in your ElevenLabs dashboard
4. Click "Save Settings"

## 4. Create Your First Podcast

1. Paste or upload a script in this format:
   ```
   Speaker A: Welcome to the show!
   Speaker B: Thanks for having me!
   ```

2. Click "Validate Script" to check formatting

3. Use "Generate (Dry Run)" to test without API calls

4. Click "Generate Podcast" to create the MP3
   - Output saves to `~/Downloads/podcast_output.mp3`

## 5. Build Standalone App

```bash
# Build the .app bundle
./build_app.sh

# Create DMG installer
./create_dmg.sh

# (Optional) Verify signatures
./verify_signature.sh
```

## 6. Sign and Notarize (For Distribution)

If you want to distribute the app to others:

```bash
# 1. Set up credentials
cp .env.example .env
# Edit .env with your Apple Developer info

# 2. Sign and notarize
./sign_and_notarize.sh
```

See `SIGNING_GUIDE.md` for detailed setup instructions.

The DMG will be ready to distribute!

## Tips

- Use Dry Run mode to validate your workflow before spending API credits
- The app validates script format and shows clear error messages
- Settings persist between sessions
- Each line must start with "Speaker A:" or "Speaker B:"
- Empty lines are ignored

## Troubleshooting

If the app doesn't start:
- Check that Python 3.11+ is installed
- Ensure all dependencies are installed: `uv sync`
- Check for error messages in the terminal

If audio generation fails:
- Verify your API key is correct
- Check that voice IDs are valid
- Ensure you have API credits available
- Try Dry Run mode first to test the script

If FFmpeg errors occur:
- Install FFmpeg: `brew install ffmpeg`
- Verify installation: `ffmpeg -version`
