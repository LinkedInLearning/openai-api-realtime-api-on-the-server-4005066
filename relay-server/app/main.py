"""
Real-time WebSocket Server
-------------------------
Main application entry point and FastAPI configuration.
"""

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from loguru import logger

from app.config.settings import PORT
from app.config.logging import config as log_config
from app.core.session import RealtimeSession

# Initialize FastAPI app
app = FastAPI(
    title="Real-time WebSocket Server",
    description="An example WebSocket server implementation using FastAPI",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
if log_config.log_to_file:
    logger.add(
        log_config.log_file_path,
        rotation=log_config.log_rotation,
        retention=log_config.log_retention,
        level=log_config.file_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    )

# Global session storage
active_sessions = {}

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

if __name__ == "__main__":
    logger.info(f"Starting server on port {PORT}")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    ) 