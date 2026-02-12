# Building Standalone macOS App

## Prerequisites

1. Install dependencies:
```bash
brew install create-dmg
uv sync
```

Note: FFmpeg is not required. The app uses soundfile for audio processing.

## Step 1: Create Standalone App with PyInstaller

```bash
# Install PyInstaller
uv pip install pyinstaller

# Create the app bundle
uv run pyinstaller --name="Text2Podcast" \
  --windowed \
  --onefile \
  --icon=app_icon.icns \
  --add-data="$(uv run python -c 'import nicegui; print(nicegui.__path__[0])'):nicegui" \
  --hidden-import=elevenlabs \
  --hidden-import=pydub \
  --collect-all nicegui \
  main.py
```

## Step 2: Create DMG Installer

```bash
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
```

## Alternative: Using py2app

Create `setup.py`:

```python
from setuptools import setup

APP = ['main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['nicegui', 'elevenlabs', 'pydub'],
    'iconfile': 'app_icon.icns',
    'plist': {
        'CFBundleName': 'Text2Podcast',
        'CFBundleDisplayName': 'Text to Podcast',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
```

Then build:
```bash
uv pip install py2app
uv run python setup.py py2app
```

## Notes

- The app will be in `dist/Text2Podcast.app`
- Uses soundfile for audio processing (no FFmpeg needed)
- Settings are stored in user's home directory: `~/.text2podcast_settings.json`
- Generated podcasts save to `~/Downloads/podcast_output.mp3`

## Testing

Before creating DMG, test the app:
```bash
open dist/Text2Podcast.app
```

## Troubleshooting

If the app doesn't launch:
1. Check Console.app for error messages
2. Run from Terminal to see output: `dist/Text2Podcast.app/Contents/MacOS/Text2Podcast`
3. Ensure all dependencies are included in the build
