"""
RealtimeSession Module
---------------------
Manages WebSocket connection sessions and coordinates communication between
frontend client and OpenAI API.
"""

import os
import asyncio
from typing import Optional, Dict, Any
from fastapi import WebSocket
from loguru import logger

from app.config.settings import OPENAI_MODEL, VOICE, DEFAULT_INSTRUCTIONS, TEMPERATURE, MAX_OUTPUT_TOKENS, WELCOME_INSTRUCTIONS
from app.config.logging import config as log_config
from app.core.websocket import WebSocketManager
from app.core.api import OpenAIAPIManager
from app.handlers.frontend import FrontendMessageHandler
from app.handlers.api import APIMessageHandler
from app.handlers.audio import AudioHandler
from app.tools.tools import tools

class RealtimeSession:
    """
    Manages a WebSocket connection session with a client.
    
    This class handles:
    - Connection lifecycle (connect, message handling, disconnect)
    - Message processing (both JSON and binary)
    - Session state management
    """

    def __init__(self, websocket: WebSocket):
        """Initialize a new session for a WebSocket connection."""
        self.connection_id = str(id(websocket))
        self.logger = logger.bind(connection_id=self.connection_id)
        
        # Initialize managers
        self.ws_manager = WebSocketManager(websocket, self.logger)
        self.api_manager = OpenAIAPIManager(self.logger)
        
        # Initialize handlers
        self.frontend_handler = FrontendMessageHandler(self.ws_manager, self.api_manager, self.logger)
        self.api_handler = APIMessageHandler(self.ws_manager, self.api_manager, self.logger)
        self.audio_handler = AudioHandler(self.ws_manager, self.api_manager, self.logger)
        
        # Session state
        self.modalities = ["text", "audio"]
        self.conversation_items = {}
        self.last_item_id = None
        self.current_response = None
        self.is_speech_active = False
        self.current_audio_item_id = None
        self.current_transcript = ""

    @property
    def is_connected(self) -> bool:
        """Check if the session is connected."""
        return self.ws_manager.is_connected

    @property
    def is_closed(self) -> bool:
        """Check if the session is closed."""
        return self.ws_manager.is_closed

    async def accept(self):
        """Accept the WebSocket connection and send welcome message."""
        await self.ws_manager.accept()

    async def close(self, code: int = 1000, reason: str = ""):
        """Close both front-end and API WebSocket connections."""
        await self.api_manager.close()
        await self.ws_manager.close(code, reason)
        self.conversation_items.clear()
        self.last_item_id = None
        self.current_response = None

    async def configure_session(self):
        """Configure the session with initial settings."""
        await self.api_manager.send({
            "type": "session.update",
            "session": {
                "modalities": self.modalities,
                "instructions": DEFAULT_INSTRUCTIONS,
                "voice": VOICE,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                    "create_response": True
                },
                "tools": tools,
                "tool_choice": "auto",
                "temperature": TEMPERATURE,
                "max_response_output_tokens": MAX_OUTPUT_TOKENS
            }
        })

    async def run(self):
        """Main session loop handling bidirectional communication."""
        try:
            # Setup connections
            await self.accept()
            await self.api_manager.connect()
            await self.configure_session()
            
            # Send welcome response event
            await self.api_manager.send({
                "type": "response.create",
                "response": {
                    "modalities": ["text", "audio"],
                    "instructions": WELCOME_INSTRUCTIONS
                }
            })
            
            # Create message handling tasks
            tasks = [
                asyncio.create_task(self.frontend_handler.handle_messages()),
                asyncio.create_task(self.api_handler.handle_messages())
            ]
            
            # Wait for either task to complete
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
        except Exception as e:
            self.logger.exception(f"Session error: {str(e)}")
        finally:
            await self.close() 