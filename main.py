import os
import re
import tempfile
from pathlib import Path
from typing import List, Tuple
from nicegui import ui, app, native
from elevenlabs.client import ElevenLabs
from multiprocessing import freeze_support
import json
import io
import soundfile as sf
import numpy as np

# Settings file path
SETTINGS_FILE = Path.home() / ".text2podcast_settings.json"

class ScriptParser:
    """Parse two-speaker scripts"""
    
    @staticmethod
    def parse(text: str) -> List[Tuple[str, str]]:
        """Parse script into (speaker, line) tuples"""
        lines = []
        errors = []
        
        for i, line in enumerate(text.strip().split('\n'), 1):
            line = line.strip()
            if not line:
                continue
            
            # Match "Host:" or "Guest:" format
            match = re.match(r'^(Host|Guest):\s*(.+)$', line, re.IGNORECASE)
            if match:
                speaker = match.group(1).upper()
                content = match.group(2).strip()
                if content:
                    lines.append((speaker, content))
                else:
                    errors.append(f"Line {i}: Empty content after speaker tag")
            else:
                errors.append(f"Line {i}: Invalid format. Expected 'Host:' or 'Guest:'")
        
        if errors:
            raise ValueError("\n".join(errors))
        
        if not lines:
            raise ValueError("No valid speaker lines found")
        
        return lines

class AudioProcessor:
    """Audio processing without FFmpeg dependency"""
    
    @staticmethod
    def stitch_audio_files(audio_files: List[bytes]) -> bytes:
        """Stitch audio files using soundfile (no FFmpeg needed)"""
        all_audio_data = []
        sample_rate = None
        
        for audio_bytes in audio_files:
            # Read audio from bytes
            audio_data, sr = sf.read(io.BytesIO(audio_bytes))
            
            # Ensure consistent sample rate
            if sample_rate is None:
                sample_rate = sr
            elif sr != sample_rate:
                # Simple resampling (basic, but works without scipy)
                ratio = sample_rate / sr
                new_length = int(len(audio_data) * ratio)
                audio_data = np.interp(
                    np.linspace(0, len(audio_data), new_length),
                    np.arange(len(audio_data)),
                    audio_data
                )
            
            # Normalize volume
            if len(audio_data) > 0:
                max_val = np.abs(audio_data).max()
                if max_val > 0:
                    audio_data = audio_data * (0.9 / max_val)
            
            all_audio_data.append(audio_data)
        
        # Concatenate all audio
        combined = np.concatenate(all_audio_data)
        
        # Write to bytes
        output = io.BytesIO()
        sf.write(output, combined, sample_rate, format='MP3')
        output.seek(0)
        return output.read()

class PodcastGenerator:
    """Generate podcast audio using ElevenLabs"""
    
    def __init__(self, api_key: str, voice_host: str, voice_guest: str, dry_run: bool = False):
        self.api_key = api_key
        self.voice_host = voice_host
        self.voice_guest = voice_guest
        self.dry_run = dry_run
        self.client = None if dry_run else ElevenLabs(api_key=api_key)
    
    def generate_audio(self, lines: List[Tuple[str, str]], progress_callback=None) -> bytes:
        """Generate and stitch audio clips"""
        audio_files = []
        total = len(lines)
        
        for i, (speaker, text) in enumerate(lines, 1):
            if progress_callback:
                progress_callback(i, total, f"Processing line {i}/{total}")
            
            if self.dry_run:
                # Simulate processing
                continue
            
            voice_id = self.voice_host if speaker == "HOST" else self.voice_guest
            
            # Generate audio using ElevenLabs
            audio = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2"
            )
            
            # Collect audio bytes
            audio_bytes = b""
            for chunk in audio:
                audio_bytes += chunk
            
            audio_files.append(audio_bytes)
        
        if self.dry_run:
            return b""
        
        # Stitch audio using soundfile
        return AudioProcessor.stitch_audio_files(audio_files)

class Settings:
    """Manage app settings"""
    
    @staticmethod
    def load():
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        return {
            'api_key': '',
            'voice_host': '',
            'voice_guest': ''
        }
    
    @staticmethod
    def save(settings: dict):
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)

# Global state
settings = Settings.load()

def main():
    """Main application"""
    
    @ui.page('/')
    def index():
        parsed_lines = []
        
        ui.label('Text to Podcast Converter').classes('text-3xl font-bold mb-4')
        
        # Settings section
        with ui.expansion('Settings', icon='settings').classes('w-full mb-4'):
            api_key_input = ui.input('ElevenLabs API Key', password=True, password_toggle_button=True) \
                .classes('w-full').props('outlined')
            api_key_input.value = settings.get('api_key', '')
            
            voice_host_input = ui.input('Voice ID for Host').classes('w-full').props('outlined')
            voice_host_input.value = settings.get('voice_host', '')
            
            voice_guest_input = ui.input('Voice ID for Guest').classes('w-full').props('outlined')
            voice_guest_input.value = settings.get('voice_guest', '')
            
            def save_settings():
                settings['api_key'] = api_key_input.value
                settings['voice_host'] = voice_host_input.value
                settings['voice_guest'] = voice_guest_input.value
                Settings.save(settings)
                ui.notify('Settings saved', type='positive')
            
            ui.button('Save Settings', on_click=save_settings, icon='save').props('color=primary')
        
        # Script input
        ui.label('Script Input').classes('text-xl font-bold mt-4 mb-2')
        ui.label('Format: Each line must start with "Host:" or "Guest:"').classes('text-sm text-gray-600 mb-2')
        
        script_input = ui.textarea('Paste your script here...') \
            .classes('w-full').props('outlined rows=15')
        
        async def load_file(e):
            if e.content:
                content = e.content.read().decode('utf-8')
                script_input.value = content
                ui.notify('File loaded', type='positive')
        
        ui.upload(on_upload=load_file, auto_upload=True) \
            .props('accept=.txt label="Or upload .txt file"').classes('mb-4')
        
        # Validation and preview
        validation_output = ui.label('').classes('mb-4')
        preview_container = ui.column().classes('w-full')
        
        def validate_script():
            nonlocal parsed_lines
            try:
                parsed_lines = ScriptParser.parse(script_input.value)
                validation_output.text = f'✓ Valid script: {len(parsed_lines)} lines'
                validation_output.classes('text-green-600 font-bold')
                
                # Show preview
                preview_container.clear()
                with preview_container:
                    ui.label('Preview:').classes('font-bold')
                    for speaker, text in parsed_lines[:5]:
                        ui.label(f'{speaker}: {text[:80]}...').classes('text-sm')
                    if len(parsed_lines) > 5:
                        ui.label(f'... and {len(parsed_lines) - 5} more lines').classes('text-sm text-gray-600')
                
            except ValueError as e:
                validation_output.text = f'✗ Error: {str(e)}'
                validation_output.classes('text-red-600')
                preview_container.clear()
                parsed_lines = []
        
        ui.button('Validate Script', on_click=validate_script, icon='check_circle').props('color=secondary')
        
        # Generation controls
        ui.separator().classes('my-4')
        ui.label('Generate Podcast').classes('text-xl font-bold mb-2')
        
        progress_label = ui.label('').classes('mb-2')
        progress_bar = ui.linear_progress(value=0).classes('mb-4')
        progress_bar.visible = False
        
        dry_run_checkbox = ui.checkbox('Dry Run (no API calls)', value=False)
        
        async def generate_podcast(dry_run: bool):
            if not parsed_lines:
                ui.notify('Please validate script first', type='warning')
                return
            
            if not settings.get('api_key') or not settings.get('voice_host') or not settings.get('voice_guest'):
                ui.notify('Please configure API key and voice IDs in Settings', type='warning')
                return
            
            progress_bar.visible = True
            progress_bar.value = 0
            
            def update_progress(current, total, message):
                progress_bar.value = current / total
                progress_label.text = message
            
            try:
                generator = PodcastGenerator(
                    settings['api_key'],
                    settings['voice_host'],
                    settings['voice_guest'],
                    dry_run=dry_run
                )
                
                audio_bytes = generator.generate_audio(parsed_lines, update_progress)
                
                if dry_run:
                    ui.notify(f'Dry run complete: {len(parsed_lines)} lines would be processed', type='positive')
                else:
                    # Save file
                    output_path = Path.home() / 'Downloads' / 'podcast_output.mp3'
                    with open(output_path, 'wb') as f:
                        f.write(audio_bytes)
                    ui.notify(f'Podcast saved to {output_path}', type='positive')
                
            except Exception as e:
                ui.notify(f'Error: {str(e)}', type='negative')
            finally:
                progress_bar.visible = False
                progress_label.text = ''
        
        with ui.row().classes('gap-2'):
            ui.button('Generate (Dry Run)', 
                     on_click=lambda: generate_podcast(True), 
                     icon='preview').props('color=orange')
            ui.button('Generate Podcast', 
                     on_click=lambda: generate_podcast(False), 
                     icon='mic').props('color=positive')
    
    freeze_support()  # first statement in main guard
    ui.run(native=True, port=native.find_open_port(), title='Text to Podcast', reload=False)

if __name__ in {"__main__", "__mp_main__"}:
    main()
