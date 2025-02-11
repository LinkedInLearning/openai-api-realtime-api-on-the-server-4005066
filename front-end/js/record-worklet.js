class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.processedFrames = 0;
  }

  process(inputs) {
    const input = inputs[0];
    if (input.length > 0) {
      // Convert stereo to mono if needed by averaging channels
      const float32Buffer = input.length === 2 ?
        this.stereoToMono(input[0], input[1]) :
        input[0];

      // Optional: Log every 100th frame
      // if (this.processedFrames % 100 === 0) {
      //   console.log("Processing audio frame:", {
      //     frameNumber: this.processedFrames,
      //     inputChannels: input.length,
      //     samplesPerChannel: float32Buffer.length,
      //     sampleValue: float32Buffer[0]  // Log first sample value
      //   });
      // }
      this.processedFrames++;

      const int16Buffer = this.convertFloat32ToInt16(float32Buffer);
      this.port.postMessage({ buffer: int16Buffer }, [int16Buffer.buffer]);
    }
    return true;
  }

  stereoToMono(leftChannel, rightChannel) {
    const monoBuffer = new Float32Array(leftChannel.length);
    for (let i = 0; i < leftChannel.length; i++) {
      monoBuffer[i] = (leftChannel[i] + rightChannel[i]) / 2;
    }
    return monoBuffer;
  }

  convertFloat32ToInt16(float32Array) {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      // Scale to 16-bit range and clamp
      let val = Math.floor(float32Array[i] * 0x7fff);
      val = Math.max(-0x8000, Math.min(0x7fff, val));
      int16Array[i] = val;
    }
    return int16Array;
  }
}

registerProcessor("recorder-worklet", PCMProcessor); 