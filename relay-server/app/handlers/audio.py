"""
Audio Handler Module
-----------------
Handles audio processing and transcription functionality.
"""

import base64
from typing import Optional
from loguru import logger
from loguru._logger import Logger

from app.core.websocket import WebSocketManager
from app.core.api import OpenAIAPIManager
from app.config.logging import config as log_config

class AudioHandler:
    """Handles audio processing and transcription."""
    
    def __init__(self, ws_manager: WebSocketManager, api_manager: OpenAIAPIManager, logger: Logger):
        """Initialize the audio handler."""
        self.ws_manager = ws_manager
        self.api_manager = api_manager
        self.logger = logger
        self.is_speech_active = False
        self.current_audio_item_id = None
        self.current_transcript = ""

    async def process_audio_chunk(self, audio_data: bytes) -> bool:
        """Process an incoming audio chunk."""
        if not self.api_manager.websocket:
            self.logger.warning("Received audio but no API connection")
            return False

        try:
            # Convert binary audio data to base64 for API
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Send audio chunk to API
            await self.api_manager.send({
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            })
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing audio chunk: {str(e)}")
            return False

    async def start_speech(self) -> str:
        """Start a new speech utterance."""
        if not self.is_speech_active:
            self.is_speech_active = True
            self.current_audio_item_id = f"audio_{id(self)}"
            self.current_transcript = ""
            
            self.logger.info("Speech started - new utterance detected")
            
            # Create initial message bubble with transcribing state
            await self.ws_manager.send_json({
                "type": "user_message",
                "id": self.current_audio_item_id,
                "text": "...",
                "has_audio": True,
                "is_transcribing": True
            })
            
            return self.current_audio_item_id
        return None

    async def stop_speech(self):
        """Stop the current speech utterance."""
        if self.is_speech_active:
            self.is_speech_active = False
            self.logger.info("Speech stopped")
            
            # Commit the audio buffer
            await self.api_manager.send({
                "type": "input_audio_buffer.commit"
            })

    async def clear_audio_buffer(self):
        """Clear the audio buffer."""
        await self.api_manager.send({
            "type": "input_audio_buffer.clear"
        }) 