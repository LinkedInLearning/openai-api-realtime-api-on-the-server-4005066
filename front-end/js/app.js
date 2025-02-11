import { setupAudioVisualizer } from './audioVisualizer.js';
import { setupWebSocket } from './websocket.js';
import { setupChat } from './chat.js';
import { setupAudio } from './audio.js';
import { WEBSOCKET_RELAY_SERVER } from './config.js';

// DOM Elements
const connectBtn = document.getElementById('connect-btn');
const micBtn = document.getElementById('mic-btn');
const statusOutput = document.getElementById('status');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const chatMessages = document.getElementById('chat-messages');

// Shared audio context and visualizers
let sharedAudioContext = null;
let aiVisualizer = null;
let micVisualizer = null;
let audio = null;

// WebSocket Configuration
const WS_URL = WEBSOCKET_RELAY_SERVER?.uri && WEBSOCKET_RELAY_SERVER?.route
  ? `${WEBSOCKET_RELAY_SERVER.protocol}${WEBSOCKET_RELAY_SERVER.uri}${WEBSOCKET_RELAY_SERVER.route}`
  : 'ws://localhost:8080/realtime';

// State
let isConnected = false;
let isMicEnabled = false;

// Initialize WebSocket connection and handlers
const ws = setupWebSocket(WS_URL, {
  onOpen: () => {
    isConnected = true;
    statusOutput.textContent = 'Connected';
    connectBtn.textContent = 'Disconnect';
    micBtn.disabled = false;
    chatInput.disabled = false;
    sendBtn.disabled = false;
  },
  onBeforeClose: () => {
    // Clear chat messages
    chatMessages.innerHTML = '';
  },
  onClose: () => {
    isConnected = false;
    statusOutput.textContent = 'Disconnected';
    connectBtn.textContent = 'Connect';
    micBtn.disabled = true;
    chatInput.disabled = true;
    sendBtn.disabled = true;

    if (isMicEnabled) {
      micBtn.click(); // Disable microphone
    }
  },
  onError: (error) => {
    console.error('WebSocket error:', error);
    statusOutput.textContent = 'Error: ' + error.message;
  }
});

// Initialize chat functionality
const chat = setupChat(ws, chatMessages, chatInput, sendBtn);

// Event Listeners
connectBtn.addEventListener('click', () => {
  if (isConnected) {
    ws.close();
    // Clean up audio context when disconnecting
    if (sharedAudioContext) {
      sharedAudioContext.close();
      sharedAudioContext = null;
      aiVisualizer = null;
      micVisualizer = null;
      audio = null;
    }
  } else {
    // Initialize audio context and visualizers before connecting
    if (!sharedAudioContext) {
      sharedAudioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 24000,  // Match server's sample rate exactly
        latencyHint: 'interactive'
      });
      aiVisualizer = setupAudioVisualizer('aiVisualizer', sharedAudioContext);
      micVisualizer = setupAudioVisualizer('micVisualizer', sharedAudioContext);
      audio = setupAudio(ws, micVisualizer, aiVisualizer, sharedAudioContext);
    }
    ws.connect();
  }
});

micBtn.addEventListener('click', async () => {
  try {
    if (!isMicEnabled) {
      await audio.startMicrophone();
      isMicEnabled = true;
      micBtn.textContent = 'Disable Mic';
      statusOutput.textContent = 'Microphone enabled';
    } else {
      audio.stopMicrophone();
      isMicEnabled = false;
      micBtn.textContent = 'Enable Mic';
      statusOutput.textContent = 'Microphone disabled';
    }
  } catch (error) {
    console.error('Microphone error:', error);
    statusOutput.textContent = 'Error: ' + error.message;
  }
});

// Handle page unload
window.addEventListener('beforeunload', () => {
  if (isConnected) {
    ws.close();
  }
}); 