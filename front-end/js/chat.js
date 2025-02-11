/**
 * Sets up chat functionality
 * @param {Object} ws - WebSocket instance
 * @param {HTMLElement} messagesContainer - Container for chat messages
 * @param {HTMLInputElement} input - Chat input element
 * @param {HTMLButtonElement} sendButton - Send message button
 * @returns {Object} Chat interface
 */
export function setupChat(ws, messagesContainer, input, sendButton) {
  // Add message handlers for different message types
  ws.addMessageHandler('text_delta', handleTextDelta);
  ws.addMessageHandler('transcription', handleTranscription);
  ws.addMessageHandler('control', handleControlMessage);
  ws.addMessageHandler('user_message', handleUserMessage);
  ws.addMessageHandler('assistant_message', handleAssistantMessage);

  // Message state
  let currentAssistantMessage = null;
  let lastUserMessageId = null;

  // Event listeners
  input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  sendButton.addEventListener('click', sendMessage);

  function sendMessage() {
    const text = input.value.trim();
    if (text && ws.isConnected()) {
      const message = {
        type: 'user_message',
        text: text
      };

      // Don't add the message here, wait for server echo
      input.value = '';
      ws.send(message);
    }
  }

  function handleUserMessage(message) {
    if (!message.text || !message.id) return;

    // Skip messages containing raw weather data
    if (message.text.includes('Weather data: {')) return;

    // Only add the message if we haven't seen this ID before
    if (lastUserMessageId !== message.id) {
      lastUserMessageId = message.id;
      addMessage('user', message.text);
    }
  }

  function handleAssistantMessage(message) {
    // Skip complete messages since we're handling deltas
    return;
  }

  function handleTextDelta(message) {
    if (!message.id || !message.delta) return;

    if (!currentAssistantMessage) {
      currentAssistantMessage = {
        id: message.id,
        content: message.delta
      };
      addMessage('ai', message.delta);
    } else if (currentAssistantMessage.id === message.id) {
      currentAssistantMessage.content += message.delta;
      updateLastMessage('ai', currentAssistantMessage.content);
    } else {
      currentAssistantMessage = {
        id: message.id,
        content: message.delta
      };
      addMessage('ai', message.delta);
    }
  }

  function handleTranscription(message) {
    if (!message.id || !message.text) return;
    updateLastMessage('user', message.text);
  }

  function handleControlMessage(message) {
    if (message.action === 'clear') {
      clearMessages();
    }
      // } else if (message.action === 'connected' && message.greeting) {
      //   addMessage('status', message.greeting);
      // }
    }

    function addMessage(role, content) {
      const messageDiv = document.createElement('div');
      messageDiv.className = `message ${role}-message`;

      const messageContent = document.createElement('div');
      messageContent.className = 'message-content';

      // Handle markdown-style code blocks
      const formattedContent = content.replace(
        /```([\s\S]*?)```/g,
        (_, code) => `<pre><code>${escapeHtml(code.trim())}</code></pre>`
      );

      messageContent.innerHTML = formattedContent;
      messageDiv.appendChild(messageContent);
      messagesContainer.appendChild(messageDiv);
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function updateLastMessage(role, content) {
      const messages = messagesContainer.getElementsByClassName(`${role}-message`);
      if (messages.length > 0) {
        const lastMessage = messages[messages.length - 1];
        const messageContent = lastMessage.querySelector('.message-content');
        if (messageContent) {
          messageContent.innerHTML = content;
        }
      }
    }

    function clearMessages() {
      messagesContainer.innerHTML = '';
      currentAssistantMessage = null;
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    return {
      sendMessage,
      clearMessages,
      addMessage
    };
  } 