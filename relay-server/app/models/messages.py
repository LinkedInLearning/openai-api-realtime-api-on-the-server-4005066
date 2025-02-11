"""
Message Type Definitions
----------------------
Defines message types and structures for frontend and API communication.
"""

from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field

# Frontend Message Types
class UserMessage(BaseModel):
    """Message sent by the user."""
    type: str = "user_message"
    id: str
    text: str
    has_audio: bool = False
    is_transcribing: bool = False
    error: Optional[str] = None

class AssistantMessage(BaseModel):
    """Message sent by the assistant."""
    type: str = "assistant_message"
    id: str
    text: str
    in_progress: bool = False
    final: bool = False
    is_audio_transcript: bool = False

class TextDelta(BaseModel):
    """Text delta update for streaming responses."""
    type: str = "text_delta"
    id: str
    response_id: str
    delta: str
    is_audio_transcript: bool = False

class ControlMessage(BaseModel):
    """Control message for session management."""
    type: str = "control"
    action: str
    id: Optional[str] = None
    message: Optional[str] = None
    greeting: Optional[str] = None
    timestamp: Optional[int] = None

class TranscriptionMessage(BaseModel):
    """Transcription result message."""
    type: str = "transcription"
    id: str
    text: str

# API Message Types
class Content(BaseModel):
    """Content of a conversation item."""
    type: str
    text: Optional[str] = None
    audio: Optional[str] = None

class ConversationItem(BaseModel):
    """A conversation item (message)."""
    id: str
    type: str = "message"
    role: str
    content: List[Content]

class ConversationItemEvent(BaseModel):
    """Event for creating a conversation item."""
    event_id: str
    type: str = "conversation.item.create"
    previous_item_id: Optional[str] = None
    item: ConversationItem

class ResponseEvent(BaseModel):
    """Event for creating a response."""
    event_id: str
    type: str = "response.create"
    response: Dict[str, Any]

class AudioBufferEvent(BaseModel):
    """Event for audio buffer operations."""
    type: str
    audio: Optional[str] = None

class SessionUpdateEvent(BaseModel):
    """Event for updating session settings."""
    type: str = "session.update"
    session: Dict[str, Any]

# Message Type Registry
message_types = {
    # Frontend Messages
    "user_message": UserMessage,
    "assistant_message": AssistantMessage,
    "text_delta": TextDelta,
    "control": ControlMessage,
    "transcription": TranscriptionMessage,
    
    # API Messages
    "conversation.item.create": ConversationItemEvent,
    "response.create": ResponseEvent,
    "input_audio_buffer.append": AudioBufferEvent,
    "session.update": SessionUpdateEvent
} 