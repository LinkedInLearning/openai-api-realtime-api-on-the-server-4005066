# Generic Frontend for OpenAI Realtime API with WebSockets

Modified version of the Azure [RTClient Chat Sample](https://github.com/Azure-Samples/aoai-realtime-audio-sdk/tree/main/samples/middle-tier/generic-frontend) provide as part of the [`azure-realtime-audio-sdk`](https://github.com/Azure-Samples/aoai-realtime-audio-sdk).

A Next.js-based chat application demonstrating the usage a custom WebSockets relay server for real-time conversations with OpenAI's Realtime API. This sample showcases text and audio interactions, streaming responses, and various configuration options.

## Features

- 🔄 Real-time text and audio conversations
- 🎙️ Audio recording and streaming playback
- 🔊 Voice Activity Detection (VAD) support
- ☁️ Support for both OpenAI and Azure OpenAI
- 🛠️ Configurable conversation settings
- 🔧 Tool integration support (coming soon)

## Prerequisites

- Node.js (version 18 or higher)
- npm or yarn
- An API key from OpenAI or Azure OpenAI
- For Azure OpenAI: deployment name and endpoint URL

## Getting Started

1. Install dependencies:
```bash
npm install
# or
yarn install
```

2. Set the WebSocket relay server URI in the `src/config.ts` file.

3. Start the development server:
```bash
npm run dev
# or
yarn dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Usage

### Middle Tier Endpoint

-  Update with your middle tier service endpoint, if needed

## Project Structure

```
src/
├── app/
│   └── page.tsx          # Main application page
├── components/
│   └── ui/              # shadcn/ui components
├── lib/
│   └── audio.ts         # Audio processing utilities
└── chat-interface.tsx   # Main chat component
```

## Dependencies

- `shadcn/ui`: UI component library
- `lucide-react`: Icon library
- Web Audio API for audio processing
