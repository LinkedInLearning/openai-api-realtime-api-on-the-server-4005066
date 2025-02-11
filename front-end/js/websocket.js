/**
 * Sets up a WebSocket connection with the server
 * @param {string} url - The WebSocket server URL
 * @param {Object} handlers - Event handlers for the WebSocket
 * @returns {Object} WebSocket interface
 */
export function setupWebSocket(url, handlers) {
  let ws = null;
  const messageHandlers = new Map();
  const binaryHandlers = new Set();

  function connect() {
    if (ws) {
      return;
    }

    ws = new WebSocket(url);
    ws.binaryType = 'arraybuffer';  // Set binary type to arraybuffer

    ws.onopen = () => {
      console.log('WebSocket connected');
      handlers.onOpen?.();
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      ws = null;
      handlers.onClose?.();
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      handlers.onError?.(error);
    };

    ws.onmessage = (event) => {
      try {
        if (event.data instanceof ArrayBuffer) {
          // Handle binary data
          binaryHandlers.forEach(handler => handler(event.data));
        } else {
          // Handle JSON data
          const message = JSON.parse(event.data);
          const handler = messageHandlers.get(message.type);
          if (handler) {
            handler(message);
          } else {
            console.warn('No handler for message type:', message.type);
          }
        }
      } catch (error) {
        console.error('Error processing message:', error);
      }
    };
  }

  function close() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        // Call onBeforeClose handler if provided
        handlers.onBeforeClose?.();
        // Send disconnect message
        send({ type: 'disconnect' });
        // Wait a small amount of time for the message to be sent
        setTimeout(() => {
          if (ws) {
            ws.close();
            ws = null;
          }
        }, 100);
      } catch (error) {
        console.log('Error during websocket closure:', error);
        // If sending fails, close anyway
        if (ws) {
          ws.close();
          ws = null;
        }
      }
    } else if (ws) {
      // If not in OPEN state, just close without sending
      ws.close();
      ws = null;
    }
  }

  function send(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      const message = JSON.stringify(data);
      ws.send(message);
    } else {
      console.error('WebSocket is not connected');
    }
  }

  function sendBinary(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(data);
    } else {
      console.error('WebSocket is not connected');
    }
  }

  function addMessageHandler(type, handler) {
    messageHandlers.set(type, handler);
  }

  function removeMessageHandler(type) {
    messageHandlers.delete(type);
  }

  function addBinaryHandler(handler) {
    binaryHandlers.add(handler);
  }

  function removeBinaryHandler(handler) {
    binaryHandlers.delete(handler);
  }

  return {
    connect,
    close,
    send,
    sendBinary,
    addMessageHandler,
    removeMessageHandler,
    addBinaryHandler,
    removeBinaryHandler,
    isConnected: () => ws?.readyState === WebSocket.OPEN
  };
} 