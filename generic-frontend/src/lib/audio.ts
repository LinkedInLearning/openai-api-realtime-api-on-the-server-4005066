// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

export class Player {
  private playbackNode: AudioWorkletNode | null = null;
  private audioContext: AudioContext | null = null;

  async init(sampleRate: number) {
    try {
      if (this.playbackNode === null) {
        this.audioContext = new AudioContext({ sampleRate });
        await this.audioContext.audioWorklet.addModule("playback-worklet.js");

        this.playbackNode = new AudioWorkletNode(this.audioContext, "playback-worklet");
        this.playbackNode.connect(this.audioContext.destination);
      }
    } catch (error) {
      console.error("Error initializing audio player:", error);
      this.cleanup();
      throw error;
    }
  }

  play(buffer: Int16Array) {
    try {
      if (this.playbackNode && this.audioContext?.state === 'running') {
        this.playbackNode.port.postMessage(buffer);
      }
    } catch (error) {
      console.error("Error playing audio:", error);
    }
  }

  clear() {
    try {
      if (this.playbackNode) {
        this.playbackNode.port.postMessage(null);
      }
    } catch (error) {
      console.error("Error clearing audio:", error);
    }
  }

  cleanup() {
    try {
      if (this.playbackNode) {
        this.playbackNode.disconnect();
        this.playbackNode = null;
      }
      if (this.audioContext) {
        this.audioContext.close();
        this.audioContext = null;
      }
    } catch (error) {
      console.error("Error cleaning up audio player:", error);
    }
  }
}

export class Recorder {
  onDataAvailable: (buffer: ArrayBuffer) => void;
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private mediaStreamSource: MediaStreamAudioSourceNode | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private isRecording: boolean = false;

  public constructor(onDataAvailable: (buffer: ArrayBuffer) => void) {
    console.log("Recorder constructor called");
    this.onDataAvailable = onDataAvailable;
  }

  async start(stream: MediaStream) {
    try {
      if (this.isRecording) {
        console.warn("Recorder is already running");
        return;
      }

      console.log("Starting recorder with stream:", {
        streamActive: stream.active,
        audioTracks: stream.getAudioTracks().length,
      });

      this.audioContext = new AudioContext({ latencyHint: "interactive", sampleRate: 24000 });
      console.log("AudioContext created with sample rate:", this.audioContext.sampleRate);

      console.log("Loading audio worklet module...");
      await this.audioContext.audioWorklet.addModule("./record-worklet.js");
      console.log("Audio worklet module loaded");

      this.mediaStream = stream;
      this.mediaStreamSource = this.audioContext.createMediaStreamSource(this.mediaStream);
      console.log("MediaStreamSource created");

      this.workletNode = new AudioWorkletNode(
        this.audioContext,
        "recorder-worklet",
        {
          numberOfInputs: 1,
          numberOfOutputs: 1,
          channelCount: 1,
          processorOptions: {
            sampleRate: this.audioContext.sampleRate,
          },
        }
      );
      console.log("WorkletNode created with config:", {
        numberOfInputs: 1,
        numberOfOutputs: 1,
        channelCount: 1,
        sampleRate: this.audioContext.sampleRate,
      });

      this.workletNode.port.onmessage = (event) => {
        if (!this.isRecording) return;
        console.log("Received audio data from worklet, size:", event.data.buffer.byteLength);
        this.onDataAvailable(event.data.buffer);
      };

      this.mediaStreamSource.connect(this.workletNode);
      this.workletNode.connect(this.audioContext.destination);
      console.log("Audio processing pipeline connected");
      this.isRecording = true;

    } catch (error) {
      console.error("Error in recorder.start():", error);
      await this.stop();
      throw error;
    }
  }

  async stop() {
    console.log("Stopping recorder");
    this.isRecording = false;

    try {
      if (this.mediaStream) {
        console.log("Stopping media stream tracks");
        this.mediaStream.getTracks().forEach((track) => track.stop());
      }
      if (this.workletNode) {
        console.log("Disconnecting worklet node");
        this.workletNode.disconnect();
      }
      if (this.mediaStreamSource) {
        console.log("Disconnecting media stream source");
        this.mediaStreamSource.disconnect();
      }
      if (this.audioContext) {
        console.log("Closing audio context");
        await this.audioContext.close();
      }
    } catch (error) {
      console.error("Error stopping recorder:", error);
    } finally {
      this.mediaStream = null;
      this.mediaStreamSource = null;
      this.workletNode = null;
      this.audioContext = null;
      console.log("Recorder cleanup complete");
    }
  }
}
