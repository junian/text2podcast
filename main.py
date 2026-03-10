import sys
import os
import re
import json
import io
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QProgressBar,
    QCheckBox, QFileDialog, QMessageBox, QGroupBox, QFormLayout,
    QScrollArea
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont, QIcon

from elevenlabs.client import ElevenLabs
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
                # Simple resampling
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
                continue
            
            voice_id = self.voice_host if speaker == "HOST" else self.voice_guest
            
            # Generate audio using ElevenLabs
            audio = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2"
            )
            
            # Collect audio bytes
            audio_bytes = b"".join(list(audio))
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

class GeneratorWorker(QThread):
    """Worker thread for audio generation to keep UI responsive"""
    progress = Signal(int, int, str)
    finished = Signal(bytes, str)
    error = Signal(str)

    def __init__(self, settings, lines, dry_run):
        super().__init__()
        self.settings = settings
        self.lines = lines
        self.dry_run = dry_run

    def run(self):
        try:
            generator = PodcastGenerator(
                self.settings['api_key'],
                self.settings['voice_host'],
                self.settings['voice_guest'],
                dry_run=self.dry_run
            )
            
            def progress_callback(current, total, message):
                self.progress.emit(current, total, message)
            
            audio_bytes = generator.generate_audio(self.lines, progress_callback)
            
            msg = f"Dry run complete: {len(self.lines)} lines would be processed" if self.dry_run else "Generation successful"
            self.finished.emit(audio_bytes, msg)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Text to Podcast Converter")
        self.setMinimumSize(800, 700)
        self.settings = Settings.load()
        self.parsed_lines = []
        self.worker = None
        
        self.setup_ui()
        self.load_settings_into_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Title
        title_label = QLabel("Text to Podcast Converter")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        # Settings Group
        settings_group = QGroupBox("Settings")
        settings_layout = QFormLayout()
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("ElevenLabs API Key")
        
        self.voice_host_input = QLineEdit()
        self.voice_host_input.setPlaceholderText("Voice ID for Host")
        
        self.voice_guest_input = QLineEdit()
        self.voice_guest_input.setPlaceholderText("Voice ID for Guest")
        
        self.save_settings_btn = QPushButton("Save Settings")
        self.save_settings_btn.clicked.connect(self.save_settings)
        
        settings_layout.addRow("API Key:", self.api_key_input)
        settings_layout.addRow("Host Voice ID:", self.voice_host_input)
        settings_layout.addRow("Guest Voice ID:", self.voice_guest_input)
        settings_layout.addRow("", self.save_settings_btn)
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # Script Input Group
        script_group = QGroupBox("Script Input")
        script_layout = QVBoxLayout()
        
        format_hint = QLabel("Format: Each line must start with 'Host:' or 'Guest:'")
        format_hint.setStyleSheet("color: gray; font-size: 11px;")
        script_layout.addWidget(format_hint)
        
        self.script_text = QTextEdit()
        self.script_text.setPlaceholderText("Paste your script here...")
        script_layout.addWidget(self.script_text)
        
        file_btns_layout = QHBoxLayout()
        self.upload_btn = QPushButton("Load .txt File")
        self.upload_btn.clicked.connect(self.load_file)
        self.validate_btn = QPushButton("Validate Script")
        self.validate_btn.clicked.connect(self.validate_script)
        self.validate_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        
        file_btns_layout.addWidget(self.upload_btn)
        file_btns_layout.addWidget(self.validate_btn)
        script_layout.addLayout(file_btns_layout)
        
        script_group.setLayout(script_layout)
        main_layout.addWidget(script_group)

        # Preview and Validation Status
        self.status_label = QLabel("")
        main_layout.addWidget(self.status_label)
        
        self.preview_area = QScrollArea()
        self.preview_area.setWidgetResizable(True)
        self.preview_area.setMaximumHeight(150)
        self.preview_content = QLabel("Preview will appear here after validation.")
        self.preview_content.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.preview_content.setWordWrap(True)
        self.preview_area.setWidget(self.preview_content)
        main_layout.addWidget(self.preview_area)

        # Generation Group
        gen_group = QGroupBox("Generate Podcast")
        gen_layout = QVBoxLayout()
        
        self.dry_run_cb = QCheckBox("Dry Run (no API calls)")
        gen_layout.addWidget(self.dry_run_cb)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        gen_layout.addWidget(self.progress_bar)
        
        self.progress_msg = QLabel("")
        gen_layout.addWidget(self.progress_msg)
        
        gen_btns_layout = QHBoxLayout()
        self.generate_btn = QPushButton("Generate Podcast")
        self.generate_btn.clicked.connect(self.start_generation)
        self.generate_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        gen_btns_layout.addWidget(self.generate_btn)
        
        gen_layout.addLayout(gen_btns_layout)
        gen_group.setLayout(gen_layout)
        main_layout.addWidget(gen_group)

    def load_settings_into_ui(self):
        self.api_key_input.setText(self.settings.get('api_key', ''))
        self.voice_host_input.setText(self.settings.get('voice_host', ''))
        self.voice_guest_input.setText(self.settings.get('voice_guest', ''))

    def save_settings(self):
        self.settings['api_key'] = self.api_key_input.text()
        self.settings['voice_host'] = self.voice_host_input.text()
        self.settings['voice_guest'] = self.voice_guest_input.text()
        Settings.save(self.settings)
        QMessageBox.information(self, "Success", "Settings saved successfully.")

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Script", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.script_text.setPlainText(f.read())
                self.status_label.setText("File loaded.")
                self.status_label.setStyleSheet("color: green;")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load file: {str(e)}")

    def validate_script(self):
        try:
            text = self.script_text.toPlainText()
            self.parsed_lines = ScriptParser.parse(text)
            self.status_label.setText(f"✓ Valid script: {len(self.parsed_lines)} lines")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            
            # Show preview
            preview_text = "<b>Preview:</b><br/>"
            for speaker, text in self.parsed_lines[:5]:
                snippet = (text[:80] + '...') if len(text) > 80 else text
                preview_text += f"<i>{speaker}</i>: {snippet}<br/>"
            if len(self.parsed_lines) > 5:
                preview_text += f"<br/>... and {len(self.parsed_lines) - 5} more lines"
            
            self.preview_content.setText(preview_text)
        except ValueError as e:
            self.status_label.setText(f"✗ Error: {str(e)}")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.preview_content.setText("Validation failed.")
            self.parsed_lines = []

    def start_generation(self):
        if not self.parsed_lines:
            QMessageBox.warning(self, "Warning", "Please validate script first.")
            return
        
        if not self.settings.get('api_key') or not self.settings.get('voice_host') or not self.settings.get('voice_guest'):
            QMessageBox.warning(self, "Warning", "Please configure API key and voice IDs in Settings.")
            return

        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.worker = GeneratorWorker(self.settings, self.parsed_lines, self.dry_run_cb.isChecked())
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.generation_finished)
        self.worker.error.connect(self.generation_error)
        self.worker.start()

    @Slot(int, int, str)
    def update_progress(self, current, total, message):
        self.progress_bar.setValue(int((current / total) * 100))
        self.progress_msg.setText(message)

    @Slot(bytes, str)
    def generation_finished(self, audio_bytes, message):
        self.generate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_msg.setText("")
        
        if self.dry_run_cb.isChecked():
            QMessageBox.information(self, "Complete", message)
        else:
            try:
                downloads_path = Path.home() / 'Downloads'
                output_path = downloads_path / 'podcast_output.mp3'
                with open(output_path, 'wb') as f:
                    f.write(audio_bytes)
                QMessageBox.information(self, "Success", f"Podcast saved to {output_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")

    @Slot(str)
    def generation_error(self, error_msg):
        self.generate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_msg.setText("")
        QMessageBox.critical(self, "Error", f"Generation failed: {error_msg}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
