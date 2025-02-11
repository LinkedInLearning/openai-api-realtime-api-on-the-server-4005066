"""
Frontend Message Handler Module
----------------------------
Handles messages received from the frontend client.
"""

import json
from typing import Optional
from fastapi import WebSocketDisconnect
from loguru import logger
from loguru._logger import Logger

from app.core.websocket import WebSocketManager
from app.core.api import OpenAIAPIManager
from app.config.settings import DEFAULT_INSTRUCTIONS, TEMPERATURE, MAX_OUTPUT_TOKENS

class FrontendMessageHandler:
    """Handles messages from the frontend client."""
    
    def __init__(self, ws_manager: WebSocketManager, api_manager: OpenAIAPIManager, logger: Logger):
        """Initialize the frontend message handler."""
        self.ws_manager = ws_manager
        self.api_manager = api_manager
        self.logger = logger
        self.is_speech_active = False
        self.current_audio_item_id = None
        self.last_item_id = None

    async def handle_audio_chunk(self, audio_data: bytes):
        """Handle incoming audio chunk from the client."""
        if not self.api_manager.websocket:
            self.logger.warning("Received audio but no API connection")
            return

        try:
            # If this is the first chunk of a new utterance
            if not self.is_speech_active:
                self.is_speech_active = True
                self.current_audio_item_id = f"audio_{id(self)}"
                
                self.logger.info("Speech started - new utterance detected")
                
                # Create initial message bubble with transcribing state
                await self.ws_manager.send_json({
                    "type": "user_message",
                    "id": self.current_audio_item_id,
                    "text": "...",
                    "has_audio": True,
                    "is_transcribing": True
                })

            # Convert binary audio data to base64 for API
            try:
                import base64
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            except Exception as e:
                self.logger.error(f"Error encoding audio data: {str(e)}")
                return

            # Send audio chunk to API
            try:
                await self.api_manager.send({
                    "type": "input_audio_buffer.append",
                    "audio": audio_base64
                })
            except Exception as e:
                self.logger.error(f"Error sending audio to API: {str(e)}")
                # If we fail to send to API, stop speech capture
                self.is_speech_active = False
                await self.ws_manager.send_json({
                    "type": "user_message",
                    "id": self.current_audio_item_id,
                    "text": "Failed to send audio",
                    "has_audio": True,
                    "is_transcribing": False,
                    "error": "Failed to send audio to API"
                })

        except Exception as e:
            self.logger.error(f"Error handling audio chunk: {str(e)}")
            self.logger.exception("Full traceback:")

    async def handle_text_message(self, text: str):
        """Handle text message from the client."""
        if not text:
            self.logger.warning("Received empty user message")
            return
            
        # Generate message ID
        item_id = f"msg_{id(self)}"
        event_id = f"event_{id(self)}"
        
        # Create API conversation item event
        api_event = {
            "event_id": event_id,
            "type": "conversation.item.create",
            "previous_item_id": self.last_item_id,
            "item": {
                "id": item_id,
                "type": "message",
                "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": text
                }]
            }
        }
        
        # Send to API
        await self.api_manager.send(api_event)
        
        # For text input, create text-only response
        response_event = {
            "event_id": f"event_{id(self)}",
            "type": "response.create",
            "response": {
                "modalities": ["text"],  # Text-only for text input
                "instructions": DEFAULT_INSTRUCTIONS,
                "temperature": TEMPERATURE,
                "max_output_tokens": MAX_OUTPUT_TOKENS
            }
        }
        
        # Send to API
        await self.api_manager.send(response_event)
        self.last_item_id = item_id

    async def handle_disconnect(self):
        """Handle disconnect request from the client."""
        self.logger.info("Received disconnect request from client")
        # Send final message before disconnecting
        try:
            await self.ws_manager.send_json({
                "type": "control",
                "action": "disconnected",
                "message": "Disconnected from server"
            })
        except Exception:
            pass
        await self.ws_manager.close()
        return True

    async def handle_message(self, message: dict) -> bool:
        """Process incoming messages from the frontend client."""
        if not self.ws_manager.is_connected or self.ws_manager.is_closed:
            return False

        if message.get("type") == "websocket.receive":
            if "bytes" in message:
                await self.handle_audio_chunk(message["bytes"])
                return False
            elif "text" in message:
                try:
                    data = json.loads(message["text"])
                    msg_type = data.get("type")
                    
                    if msg_type == "disconnect":
                        return await self.handle_disconnect()
                    elif msg_type == "user_message":
                        await self.handle_text_message(data.get("text", ""))
                    else:
                        self.logger.warning(f"Unhandled front-end message type: {msg_type}")
                    
                except json.JSONDecodeError:
                    self.logger.error("Invalid JSON message received")
            
        return False

    async def handle_messages(self):
        """Main loop for handling frontend messages."""
        try:
            while not self.ws_manager.is_closed:
                try:
                    # Check if the websocket is already closed
                    if self.ws_manager.websocket.client_state.name == "DISCONNECTED":
                        break
                        
                    message = await self.ws_manager.receive()
                    should_stop = await self.handle_message(message)
                    if should_stop:
                        break
                except WebSocketDisconnect:
                    self.logger.info("Front-end client disconnected")
                    break
                except RuntimeError as e:
                    if "disconnect message has been received" in str(e):
                        self.logger.info("WebSocket disconnect message received")
                        break
                    raise
        except Exception as e:
            if not self.ws_manager.is_closed:  # Only log error if not already closing
                self.logger.error(f"Error handling front-end messages: {str(e)}")
        finally:
            await self.ws_manager.close() 