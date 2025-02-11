"""
OpenAI API Manager Module
-----------------------
Handles OpenAI API WebSocket connection and messaging.
"""

import os
import json
import websockets
from loguru import logger
from loguru._logger import Logger
from dotenv import load_dotenv

from app.config.settings import OPENAI_MODEL
from app.config.logging import config as log_config

# Load environment variables
load_dotenv()

class OpenAIAPIManager:
    """Manages OpenAI API WebSocket connection and messaging."""
    
    def __init__(self, logger: Logger):
        """Initialize the API manager."""
        self.logger = logger
        self.websocket = None
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.model = OPENAI_MODEL
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.api_url = f"wss://api.openai.com/v1/realtime?model={self.model}"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }

    async def connect(self):
        """Establish WebSocket connection to the OpenAI API."""
        if not self.websocket:
            try:
                self.websocket = await websockets.connect(
                    self.api_url,
                    additional_headers=self.headers
                )
                self.logger.info(f"Connected to OpenAI API websocket using model: {self.model}")
            except Exception as e:
                self.logger.error(f"Failed to connect to OpenAI API: {str(e)}")
                raise

    async def close(self):
        """Close the API WebSocket connection."""
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                self.logger.error(f"Error closing API websocket: {str(e)}")
            finally:
                self.websocket = None
                self.logger.info("Closed API websocket connection")

    async def send(self, data: dict):
        """Send data to the OpenAI API websocket."""
        if self.websocket:
            try:
                message = json.dumps(data)
                
                # Log based on message type and configuration
                if "audio" in data:
                    if log_config.should_log_event('api_audio'):
                        self.logger.debug(f"Sending audio chunk to API, type: {data.get('type')}")
                else:
                    if log_config.should_log_event('api_messages'):
                        msg = f"Sending to API: {data.get('type')}"
                        if log_config.should_log_data('api_messages'):
                            msg += f", data: {message}"
                        self.logger.debug(msg)
                
                await self.websocket.send(message)
            except Exception as e:
                if log_config.should_log_event('errors'):
                    self.logger.error(f"Error sending to API: {str(e)}")
                raise

    async def receive(self) -> str:
        """Receive a message from the API."""
        if self.websocket:
            return await self.websocket.recv() 