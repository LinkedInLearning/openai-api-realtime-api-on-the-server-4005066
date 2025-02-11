class PlaybackWorklet extends AudioWorkletProcessor {
  constructor() {
    super();
    this.port.onmessage = this.handleMessage.bind(this);
    this.buffer = [];
  }

  handleMessage(event) {
    if (event.data === null) {
      this.buffer = [];
      return;
    }
    // Ensure we're handling Int16Array data
    if (event.data instanceof Int16Array) {
      this.buffer.push(...event.data);
    }
  }

  process(inputs, outputs, parameters) {
    const output = outputs[0];
    const channel = output[0];

    if (this.buffer.length > 0) {
      if (this.buffer.length >= channel.length) {
        // We have enough samples for this frame
        const samples = this.buffer.splice(0, channel.length);
        for (let i = 0; i < channel.length; i++) {
          // Convert from 16-bit PCM to float32 (-1.0 to 1.0)
          channel[i] = samples[i] / 32768.0;
        }
      } else {
        // Use what we have and fill the rest with silence
        const samples = this.buffer.splice(0, this.buffer.length);
        for (let i = 0; i < channel.length; i++) {
          channel[i] = i < samples.length ? samples[i] / 32768.0 : 0;
        }
      }
    } else {
      // No samples available, output silence
      channel.fill(0);
    }

    return true;
  }
}

registerProcessor("playback-worklet", PlaybackWorklet); 