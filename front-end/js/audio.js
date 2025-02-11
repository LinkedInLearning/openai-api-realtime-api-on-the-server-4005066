/**
 * Sets up audio functionality for recording and playback
 * @param {Object} ws - WebSocket instance
 * @param {Object} micVisualizer - Microphone visualizer instance
 * @param {Object} aiVisualizer - AI audio visualizer instance
 * @param {AudioContext} audioContext - Shared AudioContext instance
 * @returns {Object} Audio interface
 */
export function setupAudio(ws, micVisualizer, aiVisualizer, audioContext) {
  let mediaStream = null;
  let microphoneNode = null;
  let workletNode = null;
  let playbackNode = null;

  // Constants for PCM16 format
  const SAMPLE_RATE = 24000;
  const CHANNELS = 1;

  // Initialize playback node
  async function initPlayback() {
    if (!playbackNode) {
      await audioContext.audioWorklet.addModule('./js/playback-worklet.js');
      playbackNode = new AudioWorkletNode(audioContext, 'playback-worklet', {
        numberOfInputs: 0,
        numberOfOutputs: 1,
        outputChannelCount: [CHANNELS]
      });
      playbackNode.connect(audioContext.destination);
      aiVisualizer.connectSource(playbackNode);
    }
  }

  // Add message handlers
  ws.addMessageHandler('error', handleErrorMessage);
  ws.addBinaryHandler(handleAudioData);
  ws.addMessageHandler('control', (message) => {
    if (message.action === 'speech_started') {
      console.log('Speech started', message);
      if (playbackNode) {
        playbackNode.port.postMessage(null); // Clear the buffer
      }
    } else if (message.action === 'speech_stopped') {
      console.log('Speech stopped', message);
    }
  });

  async function startMicrophone() {
    try {
      // Request microphone access with exact PCM16 requirements
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          channelCount: CHANNELS,
          sampleRate: SAMPLE_RATE
        }
      });

      // Set up microphone node
      microphoneNode = audioContext.createMediaStreamSource(mediaStream);

      // Load and create audio worklet
      await audioContext.audioWorklet.addModule('./js/record-worklet.js');
      workletNode = new AudioWorkletNode(audioContext, 'recorder-worklet', {
        numberOfInputs: 1,
        numberOfOutputs: 1,
        channelCount: CHANNELS,
        processorOptions: {
          sampleRate: SAMPLE_RATE
        }
      });

      // Set up worklet message handler
      workletNode.port.onmessage = (event) => {
        if (event.data && event.data.buffer) {
          // The buffer is already an Int16Array, just send it
          ws.sendBinary(event.data.buffer.buffer);
        }
      };

      // Connect microphone to worklet and visualizer
      microphoneNode.connect(workletNode);
      micVisualizer.connectSource(microphoneNode);

      // Initialize playback if not already done
      await initPlayback();

    } catch (error) {
      console.error('Error accessing microphone:', error);
      throw error;
    }
  }

  function stopMicrophone() {
    if (workletNode) {
      workletNode.disconnect();
      workletNode = null;
    }

    if (microphoneNode) {
      microphoneNode.disconnect();
      microphoneNode = null;
    }

    if (mediaStream) {
      mediaStream.getTracks().forEach(track => track.stop());
      mediaStream = null;
    }

    if (playbackNode) {
      playbackNode.port.postMessage(null); // Clear the buffer
    }
  }

  async function handleAudioData(arrayBuffer) {
    try {
      if (!playbackNode) {
        await initPlayback();
      }

      // Create Int16Array directly from the ArrayBuffer
      const int16Array = new Int16Array(arrayBuffer);
      playbackNode.port.postMessage(int16Array);
    } catch (error) {
      console.error('Error playing audio:', error);
    }
  }

  function handleErrorMessage(message) {
    console.error('Audio error:', message.content);
  }

  return {
    startMicrophone,
    stopMicrophone
  };
} 