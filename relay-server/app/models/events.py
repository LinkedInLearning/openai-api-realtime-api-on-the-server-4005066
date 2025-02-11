"""
Event Type Definitions
-------------------
Defines event types and structures for WebSocket communication.
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel

class WebSocketState(str, Enum):
    """WebSocket connection states."""
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"

class ConnectionEvent(BaseModel):
    """Connection-related events."""
    type: str = "connection"
    state: WebSocketState
    client_host: Optional[str] = None
    connection_id: Optional[str] = None
    error: Optional[str] = None

class DisconnectReason(str, Enum):
    """Reasons for disconnection."""
    CLIENT_REQUESTED = "client_requested"
    SERVER_CLOSED = "server_closed"
    ERROR = "error"
    TIMEOUT = "timeout"
    NORMAL = "normal"

class DisconnectionEvent(BaseModel):
    """Disconnection-related events."""
    type: str = "disconnection"
    reason: DisconnectReason
    code: int = 1000
    message: Optional[str] = None

class AudioState(str, Enum):
    """Audio processing states."""
    STARTED = "started"
    STOPPED = "stopped"
    PROCESSING = "processing"
    CLEARED = "cleared"
    ERROR = "error"

class AudioEvent(BaseModel):
    """Audio-related events."""
    type: str = "audio"
    state: AudioState
    item_id: Optional[str] = None
    timestamp: Optional[int] = None
    error: Optional[str] = None

class ResponseState(str, Enum):
    """Response processing states."""
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"

class ResponseEvent(BaseModel):
    """Response-related events."""
    type: str = "response"
    state: ResponseState
    response_id: str
    item_id: Optional[str] = None
    error: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None

class TranscriptionState(str, Enum):
    """Transcription processing states."""
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class TranscriptionEvent(BaseModel):
    """Transcription-related events."""
    type: str = "transcription"
    state: TranscriptionState
    item_id: str
    text: Optional[str] = None
    error: Optional[str] = None

# Event Type Registry
event_types = {
    "connection": ConnectionEvent,
    "disconnection": DisconnectionEvent,
    "audio": AudioEvent,
    "response": ResponseEvent,
    "transcription": TranscriptionEvent
} 