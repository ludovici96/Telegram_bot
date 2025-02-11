import os
import uuid
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
import logging

logger = logging.getLogger(__name__)

class TextToSpeechService:
    def __init__(self, api_key_file: str):
        try:
            with open(api_key_file, 'r') as f:
                self.api_key = f.read().strip()
            logger.debug(f"Initialized TextToSpeechService with API key from {api_key_file}")
        except Exception as e:
            logger.error(f"Failed to read API key from {api_key_file}: {e}")
            self.api_key = None
        self.client = ElevenLabs(api_key=self.api_key)
        
    async def generate_speech(self, text: str, output_path: str) -> str:
        """
        Generate speech from text using ElevenLabs API
        
        Args:
            text (str): Text to convert to speech
            output_path (str): Path to save the audio file
            
        Returns:
            str: Path to the generated audio file
        """
        try:
            # Generate audio using ElevenLabs
            response = self.client.text_to_speech.convert(
                voice_id="pqHfZKP75CvOlQylNhV4",  # Bill voice
                output_format="mp3_22050_32",
                text=text,
                model_id="eleven_turbo_v2_5",
                voice_settings=VoiceSettings(
                    stability=0.0,
                    similarity_boost=1.0,
                    style=0.0,
                    use_speaker_boost=True,
                )
            )
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save the audio file
            with open(output_path, "wb") as f:
                for chunk in response:
                    if chunk:
                        f.write(chunk)
                        
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            raise
