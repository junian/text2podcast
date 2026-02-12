import os
import re
import tempfile
from pathlib import Path
from typing import List, Tuple
from nicegui import ui, app, native
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment
from multiprocessing import freeze_support
import json

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
            
            # Match "Speaker A:" or "Speaker B:" format
            match = re.match(r'^(Speaker [AB]):\s*(.+)$', line, re.IGNORECASE)
            if match:
                speaker = match.group(1).upper()
                content = match.group(2).strip()
                if content:
                    lines.append((speaker, content))
                else:
                    errors.append(f"Line {i}: Empty content after speaker tag")
            else:
                errors.append(f"Line {i}: Invalid format. Expected 'Speaker A:' or 'Speaker B:'")
        
        if errors:
            raise ValueError("\n".join(errors))
        
        if not lines:
            raise ValueError("No valid speaker lines found")
        
        return lines

class PodcastGenerator:
    """Generate podcast audio using ElevenLabs"""
    
    def __init__(self, api_key: str, voice_a: str, voice_b: str, dry_run: bool = False):
        self.api_key = api_key
        self.voice_a = voice_a
        self.voice_b = voice_b
        self.dry_run = dry_run
        self.client = None if dry_run else ElevenLabs(api_key=api_key)
    
    def generate_audio(self, lines: List[Tuple[str, str]], progress_callback=None) -> bytes:
        """Generate and stitch audio clips"""
        audio_segments = []
        total = len(lines)
        
        for i, (speaker, text) in enumerate(lines, 1):
            if progress_callback:
                progress_callback(i, total, f"Processing line {i}/{total}")
            
            if self.dry_run:
                # Simulate processing
                continue
            
            voice_id = self.voice_a if speaker == "SPEAKER A" else self.voice_b
            
            # Generate audio using ElevenLabs
            audio = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2"
            )
            
            # Convert to AudioSegment
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                for chunk in audio:
                    tmp.write(chunk)
                tmp_path = tmp.name
            
            segment = AudioSegment.from_mp3(tmp_path)
            os.unlink(tmp_path)
            
            # Normalize volume
            segment = segment.normalize()
            audio_segments.append(segment)
        
        if self.dry_run:
            return b""
        
        # Stitch all segments
        final_audio = sum(audio_segments)
        
        # Export to bytes
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            final_audio.export(tmp.name, format='mp3')
            tmp_path = tmp.name
        
        with open(tmp_path, 'rb') as f:
            audio_bytes = f.read()
        
        os.unlink(tmp_path)
        return audio_bytes

class Settings:
    """Manage app settings"""
    
    @staticmethod
    def load():
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        return {
            'api_key': '',
            'voice_a': '',
            'voice_b': ''
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
            
            voice_a_input = ui.input('Voice ID for Speaker A').classes('w-full').props('outlined')
            voice_a_input.value = settings.get('voice_a', '')
            
            voice_b_input = ui.input('Voice ID for Speaker B').classes('w-full').props('outlined')
            voice_b_input.value = settings.get('voice_b', '')
            
            def save_settings():
                settings['api_key'] = api_key_input.value
                settings['voice_a'] = voice_a_input.value
                settings['voice_b'] = voice_b_input.value
                Settings.save(settings)
                ui.notify('Settings saved', type='positive')
            
            ui.button('Save Settings', on_click=save_settings, icon='save').props('color=primary')
        
        # Script input
        ui.label('Script Input').classes('text-xl font-bold mt-4 mb-2')
        ui.label('Format: Each line must start with "Speaker A:" or "Speaker B:"').classes('text-sm text-gray-600 mb-2')
        
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
            
            if not settings.get('api_key') or not settings.get('voice_a') or not settings.get('voice_b'):
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
                    settings['voice_a'],
                    settings['voice_b'],
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
