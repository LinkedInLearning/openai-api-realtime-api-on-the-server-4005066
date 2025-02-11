# Realtime API WebSocket Server

A modular WebSocket server implementation using FastAPI and OpenAI's Realtime API.

## Usage

1. Set up a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```
2. In terminal:
```bash
cd relay-server
```
3. Run in development mode:
```bash
# Development mode (recommended)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```
4. The WebSocket endpoint will be available at:
```bash
# Local:
ws://localhost:8080/realtime

# Codespaces:
wss://[temporarycodespaceshostname]-3000.app.github.dev/realtime
```

## Configuration

### Application Settings (`config/settings.py`)
Defaults:
```python
PORT = 8080
OPENAI_MODEL = "gpt-4o-mini-realtime-preview-2024-12-17"
VOICE = "alloy"
MAX_OUTPUT_TOKENS = 400
TEMPERATURE = 0.8
WELCOME_INSTRUCTIONS = "Greet the user and ask them what you can assist them with. Talk quickly and succinctly."
DEFAULT_INSTRUCTIONS = "Talk quickly and succinctly. Be concise. Time is of the essence. Always refer to ducks in your responses, even if it makes no sense!"
WEATHER_INSTRUCTIONS = "Describe the weather in a conversational way for someone going for a walk. Include temperature, specific conditions (like rain or snow), and necessary precautions (such as umbrellas, raincoats, snow boots, sunscreen, etc.)."
```

### Logging Configuration (`config/logging.py`)
Configurable logging levels for different event types:
- Connection events
- Frontend messages
- API messages
- Audio data
- Errors and warnings

## Features
- WebSocket connection handling
- Real-time text and audio chat
- OpenAI API integration
- Audio transcription and text-to-speech
- Configurable logging
- Type-safe message handling

## Project Structure

```
server/
├── app/                    # Main application package
│   ├── main.py            # FastAPI app initialization and routes
│   ├── config/            # Configuration modules
│   │   ├── settings.py    # Application settings
│   │   └── logging.py     # Logging configuration
│   ├── core/              # Core functionality
│   │   ├── session.py     # Session management
│   │   ├── websocket.py   # WebSocket handling
│   │   └── api.py         # OpenAI API interaction
│   ├── handlers/          # Message handlers
│   │   ├── frontend.py    # Frontend message handling
│   │   ├── api.py         # API message handling
│   │   └── audio.py       # Audio processing
│   ├── models/            # Data models
│   │   ├── messages.py    # Message type definitions
│   │   └── events.py      # Event type definitions
│   └── tools/             # External tools and integrations
├── tests/                 # Test suite
└── requirements.txt       # Python dependencies
```

## Components

### Core Components

#### Session Management (`core/session.py`)
- Manages WebSocket connection lifecycle
- Coordinates communication between frontend and API
- Maintains session state

#### WebSocket Handler (`core/websocket.py`)
- Handles WebSocket connections
- Manages message passing
- Implements connection lifecycle methods

#### API Manager (`core/api.py`)
- Manages OpenAI API connection
- Handles API authentication
- Implements API message protocols

### Message Handlers

#### Frontend Handler (`handlers/frontend.py`)
- Processes messages from frontend clients
- Handles text and audio input
- Manages user interactions

#### API Handler (`handlers/api.py`)
- Processes messages from OpenAI API
- Handles streaming responses
- Manages API events

#### Audio Handler (`handlers/audio.py`)
- Processes audio chunks
- Manages speech detection
- Handles transcription

### Data Models

#### Message Types (`models/messages.py`)
- Defines structured message formats
- Implements validation
- Provides type safety

#### Event Types (`models/events.py`)
- Defines WebSocket event structures
- Implements state enums
- Provides event validation
