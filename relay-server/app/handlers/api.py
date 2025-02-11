"""
API Message Handler Module
-----------------------
Handles messages received from the OpenAI API.
"""

import json
from typing import Optional, Dict, Any
from loguru import logger
from loguru._logger import Logger
import websockets

from app.core.websocket import WebSocketManager
from app.core.api import OpenAIAPIManager
from app.config.logging import config as log_config
from app.tools.weatherLookup import get_weather_data

class APIMessageHandler:
    """Handles messages from the OpenAI API."""
    
    def __init__(self, ws_manager: WebSocketManager, api_manager: OpenAIAPIManager, logger: Logger):
        """Initialize the API message handler."""
        self.ws_manager = ws_manager
        self.api_manager = api_manager
        self.logger = logger
        self.current_response: Optional[Dict[str, Any]] = None
        self.current_transcript = ""  # Add transcript accumulator

    async def handle_conversation_item_created(self, data: dict):
        """Handle conversation item creation events."""
        item = data.get("item", {})
        content_array = item.get("content", [])
        item_id = item.get("id")
        
        if item.get("role") == "user":
            # Only process content if it exists
            if content_array:
                content = content_array[0]
                if content.get("type") == "input_audio":
                    # For audio input, create initial message with placeholder
                    self.logger.info("Audio message created, waiting for transcription")
                    await self.ws_manager.send_json({
                        "type": "user_message",
                        "id": item_id,
                        "text": "...",
                        "has_audio": True,
                        "is_transcribing": True
                    })
                    
                    # If audio content is present, send it
                    if "audio" in content:
                        try:
                            import base64
                            audio_bytes = base64.b64decode(content["audio"])
                            await self.ws_manager.send_bytes(audio_bytes)
                        except Exception as e:
                            self.logger.error(f"Error decoding user audio: {str(e)}")
                else:
                    # For text input
                    self.logger.info(f"User text message created: {content.get('text', '')}")
                    frontend_message = {
                        "type": "user_message",
                        "id": item_id,
                        "text": content.get("text", "")
                    }
                    await self.ws_manager.send_json(frontend_message)
            else:
                self.logger.info(f"Created empty user message with ID: {item_id}")
        elif item.get("role") == "assistant":
            # For assistant messages, handle empty content case
            if content_array:
                content = content_array[0]
                self.logger.info(f"Assistant message created: {content.get('text', '')}")
                frontend_message = {
                    "type": "assistant_message",
                    "id": item_id,
                    "text": content.get("text", "")
                }
                await self.ws_manager.send_json(frontend_message)
            else:
                self.logger.info(f"Created empty assistant message with ID: {item_id}")
                # Optionally send a placeholder message to frontend
                await self.ws_manager.send_json({
                    "type": "assistant_message",
                    "id": item_id,
                    "text": "",
                    "in_progress": True
                })

    async def handle_transcription_events(self, data: dict):
        """Handle audio transcription events."""
        item_id = data.get("item_id")
        msg_type = data.get("type")
        
        if msg_type == "conversation.item.input_audio_transcription.completed":
            transcript = data.get("transcript", "")
            self.logger.info(f"Audio transcription completed: {transcript}")
            
            # Update the message with final transcript
            await self.ws_manager.send_json({
                "type": "transcription",
                "id": item_id,
                "text": transcript
            })
        elif msg_type == "conversation.item.input_audio_transcription.failed":
            error = data.get("error", {})
            error_message = error.get("message", "Transcription failed")
            self.logger.error(f"Audio transcription failed: {error_message}")
            
            # Update the message with error
            await self.ws_manager.send_json({
                "type": "user_message",
                "id": item_id,
                "text": "Could not transcribe audio",
                "has_audio": True,
                "is_transcribing": False,
                "error": error_message
            })

    async def handle_response_events(self, data: dict):
        """Handle response-related events."""
        msg_type = data.get("type")
        response_id = data.get("response_id")
        item_id = data.get("item_id")
        
        if msg_type == "response.text.delta":
            if response_id == self.current_response.get("id"):
                delta = data.get("delta", "")
                self.logger.debug(f"Text delta received: {delta}")
                frontend_message = {
                    "type": "text_delta",
                    "id": item_id,
                    "response_id": response_id,
                    "delta": delta
                }
                await self.ws_manager.send_json(frontend_message)
        
        elif msg_type == "response.audio.delta":
            if response_id == self.current_response.get("id"):
                try:
                    import base64
                    audio_bytes = base64.b64decode(data.get("delta", ""))
                    self.logger.info(f"Audio delta received, size: {len(audio_bytes)} bytes")
                    await self.ws_manager.send_bytes(audio_bytes)
                except Exception as e:
                    self.logger.error(f"Error processing audio delta: {str(e)}")

        elif msg_type == "response.audio_transcript.delta":
            if response_id == self.current_response.get("id"):
                delta = data.get("delta", "")
                self.current_transcript += delta  # Accumulate transcript
                self.logger.debug(f"Audio transcript delta received: {delta}")
                frontend_message = {
                    "type": "text_delta",
                    "id": item_id,
                    "response_id": response_id,
                    "delta": delta,
                    "is_audio_transcript": True
                }
                await self.ws_manager.send_json(frontend_message)

        elif msg_type == "response.audio_transcript.done":
            if response_id == self.current_response.get("id"):
                self.logger.info(f"Audio transcript complete: {self.current_transcript}")
                frontend_message = {
                    "type": "assistant_message",
                    "id": item_id,
                    "text": self.current_transcript,
                    "is_audio_transcript": True,
                    "final": True
                }
                await self.ws_manager.send_json(frontend_message)
                self.current_transcript = ""  # Reset transcript
        
        elif msg_type == "response.created":
            response = data.get("response", {})
            self.current_response = {
                "id": response.get("id"),
                "status": response.get("status"),
                "output": response.get("output", [])
            }
            self.current_transcript = ""  # Reset transcript for new response
            self.logger.info(f"Response created with ID: {response.get('id')}")
        
        elif msg_type == "response.done":
            response = data.get("response", {})
            output_items = response.get("output", [])
            usage = response.get("usage", {})
            
            for item in output_items:
                if item.get("type") == "message" and item.get("role") == "assistant":
                    content = item.get("content", [{}])[0]
                    if content.get("type") == "text":
                        await self.ws_manager.send_json({
                            "type": "assistant_message",
                            "id": item.get("id"),
                            "text": content.get("text", ""),
                            "final": True
                        })
            
            if usage:
                self.logger.info(f"Response complete. Usage: {usage}")
                
            await self.ws_manager.send_json({
                "type": "control",
                "action": "response_complete",
                "id": response.get("id")
            })
            
            self.current_response = None
            self.current_transcript = ""  # Reset transcript

    async def handle_audio_buffer_events(self, data: dict):
        """Handle audio buffer related events."""
        msg_type = data.get("type")
        item_id = data.get("item_id")
        
        if msg_type == "input_audio_buffer.committed":
            self.logger.info("Audio buffer committed")
            await self.ws_manager.send_json({
                "type": "control",
                "action": "processing_speech",
                "id": item_id
            })
        
        elif msg_type == "input_audio_buffer.cleared":
            self.logger.info("Audio buffer cleared")
            await self.ws_manager.send_json({
                "type": "control",
                "action": "audio_cleared"
            })
        
        elif msg_type == "input_audio_buffer.speech_started":
            self.logger.info("API detected speech start")
            audio_start_ms = data.get("audio_start_ms")
            await self.ws_manager.send_json({
                "type": "control",
                "action": "speech_started",
                "id": item_id,
                "timestamp": audio_start_ms
            })
        
        elif msg_type == "input_audio_buffer.speech_stopped":
            self.logger.info("API detected speech end")
            audio_end_ms = data.get("audio_end_ms")
            await self.ws_manager.send_json({
                "type": "control",
                "action": "speech_stopped",
                "id": item_id,
                "timestamp": audio_end_ms
            })

    async def handle_function_call_events(self, data: dict):
        """Handle function call related events."""
        msg_type = data.get("type")
        response_id = data.get("response_id")
        item_id = data.get("item_id")
        call_id = data.get("call_id")
        
        if msg_type == "response.function_call_arguments.delta":
            if response_id == self.current_response.get("id"):
                delta = data.get("delta", "")
                self.logger.debug(f"Function call arguments delta received: {delta}")
                # We don't need to do anything with the delta, just accumulate it server-side
        
        elif msg_type == "response.function_call_arguments.done":
            if response_id == self.current_response.get("id"):
                
                try:
                    # Parse the function arguments
                    arguments = data.get("arguments", "{}")
                    args = json.loads(arguments)
                    self.logger.info(f"Function call complete with arguments: {args}")
                    
                    # Execute the weather lookup function with send_to_api as callback
                    await get_weather_data(
                        lat=args.get("lat"),
                        lon=args.get("lon"),
                        location_name=args.get("location_name"),
                        send_callback=self.api_manager.send
                    )
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Error parsing function arguments: {str(e)}")
                except Exception as e:
                    self.logger.error(f"Error executing function: {str(e)}")

    async def handle_message(self, message: str):
        """Process a message received from the API."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            # Log API response based on type
            if "audio" in data:
                if log_config.should_log_event('api_audio'):
                    self.logger.info(f"Received API audio event: {msg_type}")
            elif "delta" in data:
                if log_config.should_log_event('api_text_delta'):
                    msg = f"Received API text delta event: {msg_type}"
                    if log_config.should_log_data('api_text_delta'):
                        msg += f", delta: {data.get('delta')}"
                    self.logger.debug(msg)
            else:
                if log_config.should_log_event('api_messages'):
                    msg = f"Received API event: {msg_type}"
                    if log_config.should_log_data('api_messages'):
                        msg += f", data: {data}"
                    self.logger.info(msg)
            
            # Handle different message types
            if msg_type == "conversation.item.created":
                await self.handle_conversation_item_created(data)
            elif msg_type.startswith("conversation.item.input_audio_transcription"):
                await self.handle_transcription_events(data)
            elif msg_type.startswith("response.function_call_arguments"):
                await self.handle_function_call_events(data)
            elif msg_type.startswith("response."):
                await self.handle_response_events(data)
            elif msg_type.startswith("input_audio_buffer."):
                await self.handle_audio_buffer_events(data)
            
        except json.JSONDecodeError:
            self.logger.error("Invalid JSON message received from API")
        except Exception as e:
            self.logger.error(f"Error handling API message: {str(e)}")
            self.logger.exception("Full traceback:")

    async def handle_messages(self):
        """Main loop for handling API messages."""
        try:
            while not self.ws_manager.is_closed and self.api_manager.websocket:
                try:
                    message = await self.api_manager.receive()
                    await self.handle_message(message)
                except websockets.exceptions.ConnectionClosed:
                    self.logger.info("API websocket connection closed")
                    break
        except Exception as e:
            self.logger.error(f"Error handling API messages: {str(e)}")
            raise 