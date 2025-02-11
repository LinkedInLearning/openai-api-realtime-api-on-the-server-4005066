"""
Logging configuration for the realtime websocket server.
Controls what events are logged and at what detail level.
"""
from enum import Enum
from typing import Dict, Optional

class LogLevel(str, Enum):
    """Log levels for different types of events"""
    NONE = "none"  # Don't log this type of event
    EVENT_ONLY = "event_only"  # Log only that the event occurred
    FULL = "full"  # Log the event and its data

class LogConfig:
    """Configuration for different types of logging events"""
    def __init__(self):
        # Connection events
        self.connection_events: LogLevel = LogLevel.FULL
        self.disconnection_events: LogLevel = LogLevel.FULL
        
        # Frontend communication
        self.frontend_messages: LogLevel = LogLevel.EVENT_ONLY
        self.frontend_audio: LogLevel = LogLevel.NONE  # Audio chunks are very noisy to log
        
        # API communication
        self.api_messages: LogLevel = LogLevel.EVENT_ONLY
        self.api_audio: LogLevel = LogLevel.NONE
        self.api_text_delta: LogLevel = LogLevel.EVENT_ONLY
        self.api_function_calls: LogLevel = LogLevel.FULL
        
        # Error events - these should typically stay at FULL
        self.errors: LogLevel = LogLevel.FULL
        self.warnings: LogLevel = LogLevel.FULL

        # File configuration
        self.log_to_file: bool = True
        self.log_file_path: str = "server.log"
        self.log_rotation: str = "500 MB"
        self.log_retention: str = "10 days"
        self.console_level: str = "INFO"
        self.file_level: str = "DEBUG"

    def should_log_data(self, event_type: str) -> bool:
        """Determine if full data should be logged for an event type"""
        config = getattr(self, event_type, LogLevel.EVENT_ONLY)
        return config == LogLevel.FULL

    def should_log_event(self, event_type: str) -> bool:
        """Determine if an event should be logged at all"""
        config = getattr(self, event_type, LogLevel.EVENT_ONLY)
        return config != LogLevel.NONE

# Create a default configuration instance
config = LogConfig() 