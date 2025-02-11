import os
import subprocess
import whisper
import torch
from pathlib import Path
from pydub import AudioSegment
import glob
import time
import numpy as np
from functools import lru_cache

class WhisperService:
    def __init__(self, model="base", device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        # aggressive torch optimizations
        torch.set_num_threads(2)
        torch.set_float32_matmul_precision('medium')
        if self.device == "cpu":
            torch.set_num_interop_threads(1)
            torch.backends.mkl.num_threads = 2
        
        # Load the model
        self.model = whisper.load_model(
            model,
            device=self.device,
            download_root=None,
            in_memory=True
        )
        
        # Set up audio folder in project root
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.audio_folder = os.path.join(root_dir, "audio")
        os.makedirs(self.audio_folder, exist_ok=True)
        
        self.temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "src", "audio")
        os.makedirs(self.temp_dir, exist_ok=True)

    def detect_voice_activity(self, audio_data, sample_rate=16000, threshold=0.01):
        """Simple Voice Activity Detection"""
        if isinstance(audio_data, str):  # If path provided
            audio = AudioSegment.from_wav(audio_data)
            samples = np.array(audio.get_array_of_samples())
        else:
            samples = audio_data
            
        # Normalize and check energy levels
        samples = samples / np.max(np.abs(samples))
        frame_length = int(0.025 * sample_rate)  # 25ms frames
        energy = np.array([sum(samples[i:i+frame_length]**2) for i in range(0, len(samples), frame_length)])
        
        return np.any(energy > threshold)

    def convert_ogg_to_wav(self, ogg_path):
        wav_path = os.path.splitext(ogg_path)[0] + '.wav'
        try:
            command = [
                'ffmpeg', '-y', 
                '-i', ogg_path,
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-loglevel', 'error',
                '-stats',
                wav_path
            ]
            subprocess.run(command, check=True, capture_output=True)
            return wav_path
        except Exception as e:
            raise

    def _transcribe(self, audio_file):
        return self.model.transcribe(
            audio_file,
            language=None,  # Set to None to enable auto-detection
            fp16=False,
            beam_size=1,
            best_of=1,
            temperature=0.0,
            condition_on_previous_text=False,
            compression_ratio_threshold=2.4,
            logprob_threshold=-1.0,
            no_speech_threshold=0.6
        )["text"].strip()

    def transcribe(self, audio_file):
        try:
            if audio_file.endswith('.ogg'):
                audio_file = self.convert_ogg_to_wav(audio_file)
            
            if not self.detect_voice_activity(audio_file):
                return ""
            
            result = self._transcribe(audio_file)
            return result
        except Exception as e:
            raise
        finally:
            self.cleanup_audio_files()

    def cleanup_audio_files(self):
        for ext in ['*.ogg', '*.wav']:
            for file in glob.glob(os.path.join(self.audio_folder, ext)):
                try:
                    os.remove(file)
                except Exception:
                    pass
            
            for file in glob.glob(os.path.join(self.temp_dir, ext)):
                try:
                    os.remove(file)
                except Exception:
                    pass