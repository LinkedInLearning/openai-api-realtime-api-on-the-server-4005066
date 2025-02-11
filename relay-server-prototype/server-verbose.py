# Standard library imports
import os
import json
from typing import Dict, Optional
import asyncio
import websockets
import base64

# Third-party imports
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import uvicorn
from dotenv import load_dotenv

# Import server configuration
from config import (
    PORT, 
    OPENAI_MODEL, 
    VOICE, 
    MAX_OUTPUT_TOKENS,
    TEMPERATURE,
    DEFAULT_INSTRUCTIONS
)

# Import logging configuration
from logging import config as log_config

# Import tools
from tools.tools import tools
from tools.weatherLookup import get_weather_data
"""
Real-time WebSocket Server Example
--------------------------------
This example demonstrates how to build a real-time WebSocket server using FastAPI.
It includes:
1. WebSocket connection handling
2. Authentication
3. JSON and binary message support
4. Session management
5. Error handling and logging

Key concepts:
- WebSocket: A protocol providing full-duplex communication channels over a single TCP connection
- Session: A class managing the state and lifecycle of each client connection
- Authentication: Basic token-based auth using Bearer tokens
- CORS: Cross-Origin Resource Sharing configuration for web security
"""

# Load environment variables from .env file
load_dotenv()

# Configure logging
if log_config.log_to_file:
    logger.add(
        log_config.log_file_path,
        rotation=log_config.log_rotation,
        retention=log_config.log_retention,
        level=log_config.file_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    )

# Initialize FastAPI app
app = FastAPI(
    title="Real-time WebSocket Server",
    description="An example WebSocket server implementation using FastAPI",
    version="1.0.0"
)

# Configure CORS
# This is important for web applications connecting from different domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        self.websocket = websocket
        self.connection_id = str(id(websocket))
        self.logger = logger.bind(connection_id=self.connection_id)
        self.is_connected = False
        self.is_closed = False
        self.modalities = ["text", "audio"]  # Support both text and audio
        self.conversation_items = {}  # Store items by ID
        self.last_item_id = None  # Track the last message for ordering
        self.api_websocket = None  # WebSocket connection to the API
        self.current_response = None  # Track current response state
        self.is_speech_active = False  # Track if user is currently speaking
        self.current_audio_item_id = None  # Track current audio message ID
        self.current_transcript = ""  # Track current transcript text
        
        # OpenAI API configuration
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.model = OPENAI_MODEL
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.api_url = f"wss://api.openai.com/v1/realtime?model={self.model}"
        self.api_headers = [
            f"Authorization: Bearer {self.api_key}",
            "OpenAI-Beta: realtime=v1"
        ]

    @property
    def client_host(self) -> str:
        """Get the client's host address."""
        return self.websocket.client.host

    async def accept(self):
        """
        Accept the WebSocket connection and send welcome message.
        """
        if not self.is_connected and not self.is_closed:
            await self.websocket.accept()
            self.is_connected = True
            
            if log_config.should_log_event('connection_events'):
                msg = f"Client connected from {self.client_host}"
                if log_config.should_log_data('connection_events'):
                    msg += f" (connection_id: {self.connection_id})"
                self.logger.info(msg)
            
            # Send control message in the expected format
            await self.send_json({
                "type": "control",
                "action": "connected",
                "greeting": "Connected to realtime server"
            })

    async def close(self, code: int = 1000, reason: str = ""):
        """Close both front-end and API WebSocket connections."""
        if not self.is_closed:
            self.is_closed = True
            self.is_connected = False
            
            try:
                # Close API connection if open
                if self.api_websocket:
                    try:
                        await self.api_websocket.close()
                    except Exception as e:
                        self.logger.error(f"Error closing API websocket: {str(e)}")
                    finally:
                        self.api_websocket = None
                    self.logger.info("Closed API websocket connection")
                
                # Try to send final disconnection message to front-end
                if self.websocket and not self.websocket.client_state.name == "DISCONNECTED":
                    try:
                        await self.websocket.send_json({
                            "type": "control",
                            "action": "disconnected",
                            "message": "Disconnected from server"
                        })
                    except Exception:
                        pass
                
                # Close front-end connection
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
                # Clear any remaining state
                self.conversation_items.clear()
                self.last_item_id = None
                self.current_response = None

    async def send_json(self, data: dict):
        """Send JSON data to the client."""
        if self.is_connected and not self.is_closed:
            await self.websocket.send_json(data)

    async def send_bytes(self, data: bytes):
        """Send binary data to the client."""
        if self.is_connected and not self.is_closed:
            await self.websocket.send_bytes(data)

    async def connect_to_api(self):
        """Establish WebSocket connection to the OpenAI API."""
        if not self.api_websocket:
            try:
                 # Create headers as a simple dictionary
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "OpenAI-Beta": "realtime=v1"
                }
                
                self.api_websocket = await websockets.connect(
                    self.api_url,
                    additional_headers=headers
                )
                self.logger.info(f"Connected to OpenAI API websocket using model: {self.model}")
            except Exception as e:
                self.logger.error(f"Failed to connect to OpenAI API: {str(e)}")
                raise

    async def send_to_api(self, data: dict):
        """Send data to the OpenAI API websocket."""
        if self.api_websocket:
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
                
                await self.api_websocket.send(message)
            except Exception as e:
                if log_config.should_log_event('errors'):
                    self.logger.error(f"Error sending to API: {str(e)}")
                raise

    async def handle_audio_chunk(self, audio_data: bytes):
        """Handle incoming audio chunk from the client."""
        if not self.api_websocket:
            self.logger.warning("Received audio but no API connection")
            return

        try:
            # If this is the first chunk of a new utterance
            if not self.is_speech_active:
                self.is_speech_active = True
                self.current_audio_item_id = f"audio_{id(self)}"
                self.current_transcript = ""  # Reset transcript for new utterance
                
                self.logger.info("Speech started - new utterance detected")
                
                # Create initial message bubble with transcribing state
                await self.send_json({
                    "type": "user_message",
                    "id": self.current_audio_item_id,
                    "text": "...",
                    "has_audio": True,
                    "is_transcribing": True
                })

            # Convert binary audio data to base64 for API
            try:
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            except Exception as e:
                self.logger.error(f"Error encoding audio data: {str(e)}")
                return

            # Send audio chunk to API
            try:
                await self.send_to_api({
                    "type": "input_audio_buffer.append",
                    "audio": audio_base64
                })
            except Exception as e:
                self.logger.error(f"Error sending audio to API: {str(e)}")
                # If we fail to send to API, stop speech capture
                self.is_speech_active = False
                await self.send_json({
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

    async def handle_message(self, message: dict):
        """
        Process incoming messages from the front-end client.
        Transform them into API events and relay responses.
        """
        if not self.is_connected or self.is_closed:
            return False

        if message.get("type") == "websocket.receive":
            if "bytes" in message:
                if log_config.should_log_event('frontend_audio'):
                    self.logger.info(f"Received audio chunk from frontend, size: {len(message['bytes'])} bytes")
                await self.handle_audio_chunk(message["bytes"])
                return False
            elif "text" in message:
                try:
                    data = json.loads(message["text"])
                    msg_type = data.get("type")
                    
                    if log_config.should_log_event('frontend_messages'):
                        msg = f"Received front-end event: {msg_type}"
                        if log_config.should_log_data('frontend_messages'):
                            msg += f", data: {data}"
                        self.logger.info(msg)
                    
                    if msg_type == "disconnect":
                        self.logger.info("Received disconnect request from client")
                        # Send final message before disconnecting
                        try:
                            await self.websocket.send_json({
                                "type": "control",
                                "action": "disconnected",
                                "message": "Disconnected from server"
                            })
                        except Exception:
                            pass
                        # Set flags and initiate close
                        self.is_closed = True
                        self.is_connected = False
                        await self.close()
                        return True
                        
                    elif msg_type == "user_message":
                        # Transform user_message into conversation.item.create
                        text = data.get("text", "")
                        if not text:
                            self.logger.warning("Received empty user message")
                            return False
                            
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
                        await self.send_to_api(api_event)
                        
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
                        await self.send_to_api(response_event)
                        
                    else:
                        self.logger.warning(f"Unhandled front-end message type: {msg_type}")
                    
                except json.JSONDecodeError:
                    self.logger.error("Invalid JSON message received")
            
        return False  # Continue the message loop

    async def handle_frontend_messages(self):
        """Handle messages from the front-end client."""
        try:
            while not self.is_closed:
                try:
                    # Check if the websocket is already closed
                    if self.websocket.client_state.name == "DISCONNECTED":
                        break
                        
                    message = await self.websocket.receive()
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
            if not self.is_closed:  # Only log error if not already closing
                self.logger.error(f"Error handling front-end messages: {str(e)}")
        finally:
            # Ensure we're marked as closed and clean up
            self.is_closed = True
            self.is_connected = False
            await self.close()

    async def handle_api_messages(self):
        """Handle messages from the API."""
        try:
            while not self.is_closed and self.api_websocket:
                try:
                    message = await self.api_websocket.recv()
                    await self.handle_api_message(message)
                except websockets.exceptions.ConnectionClosed:
                    self.logger.info("API websocket connection closed")
                    break
        except Exception as e:
            self.logger.error(f"Error handling API messages: {str(e)}")
            raise

    async def handle_api_message(self, message: str):
        """Handle messages received from the OpenAI API."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            event_id = data.get("event_id")
            
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
                    msg = f"Received API event: {msg_type} (event_id: {event_id})"
                    if log_config.should_log_data('api_messages'):
                        msg += f", data: {data}"
                    self.logger.info(msg)
            
            # Transform API events into frontend-compatible format
            if msg_type == "conversation.item.created":
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
                            await self.send_json({
                                "type": "user_message",
                                "id": item_id,
                                "text": "...",
                                "has_audio": True,
                                "is_transcribing": True
                            })
                            
                            # If audio content is present, send it
                            if "audio" in content:
                                try:
                                    audio_bytes = base64.b64decode(content["audio"])
                                    await self.send_bytes(audio_bytes)
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
                            await self.send_json(frontend_message)
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
                        await self.send_json(frontend_message)
                    else:
                        self.logger.info(f"Created empty assistant message with ID: {item_id}")
                        # Optionally send a placeholder message to frontend
                        await self.send_json({
                            "type": "assistant_message",
                            "id": item_id,
                            "text": "",
                            "in_progress": True
                        })
                    self.last_item_id = item_id

            elif msg_type == "conversation.item.input_audio_transcription.completed":
                # Handle completed transcription from API
                item_id = data.get("item_id")
                transcript = data.get("transcript", "")
                self.logger.info(f"Audio transcription completed: {transcript}")
                
                # Update the message with final transcript using transcription type
                await self.send_json({
                    "type": "transcription",
                    "id": item_id,
                    "text": transcript
                })

            elif msg_type == "conversation.item.input_audio_transcription.failed":
                # Handle failed transcription from API
                item_id = data.get("item_id")
                error = data.get("error", {})
                error_message = error.get("message", "Transcription failed")
                self.logger.error(f"Audio transcription failed: {error_message}")
                
                # Update the message with error
                await self.send_json({
                    "type": "user_message",
                    "id": item_id,
                    "text": "Could not transcribe audio",
                    "has_audio": True,
                    "is_transcribing": False,
                    "error": error_message
                })
                
            elif msg_type == "response.text.delta":
                # Handle streaming text response
                response_id = data.get("response_id")
                item_id = data.get("item_id")
                delta = data.get("delta", "")
                
                if response_id == self.current_response.get("id"):
                    self.logger.debug(f"Text delta received: {delta}")
                    frontend_message = {
                        "type": "text_delta",
                        "id": item_id,
                        "response_id": response_id,
                        "delta": delta
                    }
                    await self.send_json(frontend_message)
                else:
                    self.logger.warning(f"Received text delta for unknown response: {response_id}")
                    
            elif msg_type == "response.audio.delta":
                # Handle streaming audio response
                if "audio" in self.modalities:
                    response_id = data.get("response_id")
                    item_id = data.get("item_id")
                    
                    if response_id == self.current_response.get("id"):
                        try:
                            # Convert base64 audio to bytes
                            audio_bytes = base64.b64decode(data.get("delta", ""))
                            self.logger.info(f"Audio delta received, size: {len(audio_bytes)} bytes")  # Changed to info level, only log size
                            
                            # Send audio chunk to frontend
                            await self.send_bytes(audio_bytes)
                        except Exception as e:
                            self.logger.error(f"Error processing audio delta: {str(e)}")
                    else:
                        self.logger.warning(f"Received audio delta for unknown response: {response_id}")

            elif msg_type == "response.audio_transcript.delta":
                # Handle streaming audio transcript
                response_id = data.get("response_id")
                item_id = data.get("item_id")
                delta = data.get("delta", "")
                
                if response_id == self.current_response.get("id"):
                    self.logger.debug(f"Audio transcript delta received: {delta}")
                    frontend_message = {
                        "type": "text_delta",
                        "id": item_id,
                        "response_id": response_id,
                        "delta": delta,
                        "is_audio_transcript": True
                    }
                    await self.send_json(frontend_message)
                else:
                    self.logger.warning(f"Received audio transcript delta for unknown response: {response_id}")

            elif msg_type == "response.audio_transcript.done":
                # Handle completed audio transcript
                response_id = data.get("response_id")
                item_id = data.get("item_id")
                transcript = data.get("transcript", "")
                
                if response_id == self.current_response.get("id"):
                    self.logger.info(f"Audio transcript complete: {transcript}")
                    frontend_message = {
                        "type": "assistant_message",
                        "id": item_id,
                        "text": transcript,
                        "is_audio_transcript": True,
                        "final": True
                    }
                    await self.send_json(frontend_message)
                else:
                    self.logger.warning(f"Received audio transcript completion for unknown response: {response_id}")

            elif msg_type == "input_audio_buffer.committed":
                self.logger.info("Audio buffer committed")
                item_id = data.get("item_id")
                # Forward buffer committed event
                await self.send_json({
                    "type": "control",
                    "action": "processing_speech",
                    "id": item_id
                })
                
                # Create response with both modalities
                response_event = {
                    "event_id": f"event_{id(self)}",
                    "type": "response.create",
                    "response": {
                        "modalities": ["text", "audio"],
                        "instructions": DEFAULT_INSTRUCTIONS,
                    }
                }
                await self.send_to_api(response_event)
                
            elif msg_type == "input_audio_buffer.cleared":
                self.logger.info("Audio buffer cleared")
                await self.send_json({
                    "type": "control",
                    "action": "audio_cleared"
                })
                
            elif msg_type == "input_audio_buffer.speech_started":
                self.logger.info("API detected speech start")
                item_id = data.get("item_id")
                audio_start_ms = data.get("audio_start_ms")
                await self.send_json({
                    "type": "control",
                    "action": "speech_started",
                    "id": item_id,
                    "timestamp": audio_start_ms
                })
                
            elif msg_type == "input_audio_buffer.speech_stopped":
                self.logger.info("API detected speech end")
                item_id = data.get("item_id")
                audio_end_ms = data.get("audio_end_ms")
                await self.send_json({
                    "type": "control",
                    "action": "speech_stopped",
                    "id": item_id,
                    "timestamp": audio_end_ms
                })
                self.is_speech_active = False
                
                # When speech stops, commit the audio buffer
                self.logger.info("Committing audio buffer")
                await self.send_to_api({
                    "type": "input_audio_buffer.commit"
                })

            elif msg_type == "response.function_call_arguments.delta":
                # Handle streaming function call arguments
                response_id = data.get("response_id")
                item_id = data.get("item_id")
                call_id = data.get("call_id")
                delta = data.get("delta", "")
                
                if response_id == self.current_response.get("id"):
                    self.logger.debug(f"Function call arguments delta received: {delta}")
                    # We don't need to do anything with the delta, just accumulate it server-side
                else:
                    self.logger.warning(f"Received function call delta for unknown response: {response_id}")

            elif msg_type == "response.function_call_arguments.done":
                # Handle completed function call
                response_id = data.get("response_id")
                item_id = data.get("item_id")
                call_id = data.get("call_id")
                arguments = data.get("arguments", "{}")
                
                if response_id == self.current_response.get("id"):
                    try:
                        # Parse the function arguments
                        args = json.loads(arguments)
                        self.logger.info(f"Function call complete with arguments: {args}")
                        
                        # Execute the weather lookup function with send_to_api as callback
                        await get_weather_data(
                            lat=args.get("lat"),
                            lon=args.get("lon"),
                            location_name=args.get("location_name"),
                            send_callback=self.send_to_api
                        )
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Error parsing function arguments: {str(e)}")
                    except Exception as e:
                        self.logger.error(f"Error executing function: {str(e)}")
                else:
                    self.logger.warning(f"Received function call completion for unknown response: {response_id}")
                
            elif msg_type == "response.created":
                # Track the response for subsequent deltas
                response = data.get("response", {})
                self.current_response = {
                    "id": response.get("id"),
                    "status": response.get("status"),
                    "output": response.get("output", [])
                }
                self.logger.info(f"Response created with ID: {response.get('id')}")
                
            elif msg_type == "response.done":
                # Process final response
                response = data.get("response", {})
                output_items = response.get("output", [])
                usage = response.get("usage", {})
                
                for item in output_items:
                    if item.get("type") == "message" and item.get("role") == "assistant":
                        content = item.get("content", [{}])[0]
                        if content.get("type") == "text":
                            await self.send_json({
                                "type": "assistant_message",
                                "id": item.get("id"),
                                "text": content.get("text", ""),
                                "final": True
                            })
                
                # Log usage statistics
                if usage:
                    self.logger.info(f"Response complete. Usage: {usage}")
                    
                await self.send_json({
                    "type": "control",
                    "action": "response_complete",
                    "id": response.get("id")
                })
                
                # Clear current response tracking
                self.current_response = None
            
        except Exception as e:
            self.logger.error(f"Error handling API message: {str(e)}")
            self.logger.exception("Full traceback:")

    async def run(self):
        """Main session loop handling bidirectional communication."""
        try:
            # Accept front-end connection
            await self.accept()
            
            # Connect to API
            await self.connect_to_api()
            
            # Configure session with audio settings AFTER API connection is established
            await self.send_to_api({
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
            
            # Create tasks for handling messages
            tasks = [
                asyncio.create_task(self.handle_frontend_messages()),
                asyncio.create_task(self.handle_api_messages())
            ]
            
            # Wait for either task to complete (indicating a disconnect)
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

# Global session storage
active_sessions: Dict[str, RealtimeSession] = {}

@app.websocket("/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint handling new connections.
    
    This endpoint:
    1. Creates a new session for each connection
    2. Stores the session in active_sessions
    3. Runs the session
    4. Cleans up after disconnection
    """
    session = RealtimeSession(websocket)
    active_sessions[session.connection_id] = session
    
    try:
        await session.run()
    finally:
        if session.connection_id in active_sessions:
            del active_sessions[session.connection_id]

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Server is running"}

# Server startup
if __name__ == "__main__":
    port = PORT
    logger.info(f"Starting server on port {port}")
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
