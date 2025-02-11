"""
WebSocket Manager Module
----------------------
Handles WebSocket connection lifecycle and message passing.
"""

from typing import Optional
from fastapi import WebSocket
from loguru import logger
from loguru._logger import Logger

from app.config.logging import config as log_config

class WebSocketManager:
    """Manages WebSocket connection and messaging."""
    
    def __init__(self, websocket: WebSocket, logger: Logger):
        """Initialize the WebSocket manager."""
        self.websocket = websocket
        self.logger = logger
        self.is_connected = False
        self.is_closed = False

    @property
    def client_host(self) -> str:
        """Get the client's host address."""
        return self.websocket.client.host

    async def accept(self):
        """Accept the WebSocket connection and send welcome message."""
        if not self.is_connected and not self.is_closed:
            await self.websocket.accept()
            self.is_connected = True
            
            if log_config.should_log_event('connection_events'):
                msg = f"Client connected from {self.client_host}"
                if log_config.should_log_data('connection_events'):
                    msg += f" (connection_id: {id(self.websocket)})"
                self.logger.info(msg)
            
            await self.send_json({
                "type": "control",
                "action": "connected",
                "greeting": "Connected to realtime server"
            })

    async def close(self, code: int = 1000, reason: str = ""):
        """Close the WebSocket connection."""
        if not self.is_closed:
            self.is_closed = True
            self.is_connected = False
            
            try:
                # Try to send final disconnection message
                if self.websocket and not self.websocket.client_state.name == "DISCONNECTED":
                    try:
                        await self.websocket.send_json({
                            "type": "control",
                            "action": "disconnected",
                            "message": "Disconnected from server"
                        })
                    except Exception:
                        pass
                
                # Close connection
                if self.websocket:
                    try:
                        await self.websocket.close(code=code, reason=reason)
                    except Exception as e:
                        if "already completed" not in str(e):
                            self.logger.error(f"Error closing websocket: {str(e)}")
            except Exception as e:
                self.logger.error(f"Error during connection close: {str(e)}")
            finally:
                self.logger.info(f"Connection closed: {reason}")

    async def send_json(self, data: dict):
        """Send JSON data to the client."""
        if self.is_connected and not self.is_closed:
            await self.websocket.send_json(data)

    async def send_bytes(self, data: bytes):
        """Send binary data to the client."""
        if self.is_connected and not self.is_closed:
            await self.websocket.send_bytes(data)

    async def receive(self) -> dict:
        """Receive a message from the client."""
        if self.is_connected and not self.is_closed:
            return await self.websocket.receive() 