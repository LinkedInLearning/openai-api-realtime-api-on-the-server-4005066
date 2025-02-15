// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    console.log("PCMProcessor constructor called");
    this.processedFrames = 0;
  }

  process(inputs) {
    const input = inputs[0];
    if (input.length > 0) {
      const float32Buffer = input[0];
      if (this.processedFrames % 100 === 0) {  // Log every 100th frame to avoid console spam
        console.log("Processing audio frame:", {
          frameNumber: this.processedFrames,
          inputChannels: input.length,
          samplesPerChannel: float32Buffer.length,
          sampleValue: float32Buffer[0]  // Log first sample value
        });
      }
      this.processedFrames++;

      const int16Buffer = this.convertFloat32ToInt16(float32Buffer);
      this.port.postMessage({ buffer: int16Buffer }, [int16Buffer.buffer]);
    }
    return true;
  }

  convertFloat32ToInt16(float32Array) {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      let val = Math.floor(float32Array[i] * 0x7fff);
      val = Math.max(-0x8000, Math.min(0x7fff, val));
      int16Array[i] = val;
    }
    return int16Array;
  }
}

registerProcessor("recorder-worklet", PCMProcessor);
