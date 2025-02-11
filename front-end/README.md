# OpenAI Realtime API wtih WebSockets - Simple Front-End Client

Simple front-end client for OpenAI Realtime API over WebSockets built using vanilla HTML, CSS, and JavaScript. 
Uses `../relay-server/` as a WebSockets relay server to communicate with the API.

Function calling uses free [Open-Meteo](https://open-meteo.com/) weather API to retrieve current weather data..

Features:
- Voice and text chat
- Function calling generating real-time weather responses

> NOTE:
> All configuration settings for the API are found in `../relay-server/app/config/settings.py`

## Getting Started

1. Set up the Relay Server (see `../relay-server/README.md`)
2. Configure the Relay Server websockets URI in `js/config.js`
   - In Codespaces:
     - Go to Ports
     - Check that `relay-server` Visibility is set to "Public"
     - Copy `relay-server` URI
     - Paste only the hostname (no "https://") in config.js
3. Run from Terminal:
```bash
cd front-end
npm run start
```

## Usage

1. Click the "Start Session" button to initialize a new chat session
2. Allow microphone access when prompted
3. Click "Unmute" to activate voice chat
4. Use the text field to enter text chat
5. Ask about the weather in a specified location, ie "What's the weather in Vancouver?"
6. Click "End Session" to terminate the chat

