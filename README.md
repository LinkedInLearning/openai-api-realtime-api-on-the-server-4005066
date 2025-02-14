# OpenAI API: Realtime API on the Server
This is the repository for the LinkedIn Learning course OpenAI API: Realtime API on the Server. The full course is available from [LinkedIn Learning][lil-course-url].

![lil-thumbnail-url]

## Course Description

With OpenAI’s Realtime API, you can build a custom real-time voice-to-voice AI chat into any app powered by a WebSockets back-end on a server. This course builds on "OpenAI API: Building Front-End Voice Apps with the Realtime API and WebRTC" and explores how to host the API integration in an agnostic server.

## Instructions
These exercise files can be used in GitHub Codespaces or in your local dev environment. Here's a breakdown of the files for reference:

- `./relay-server/`: A front-end-agnostic FastAPI Python relay server using WebSockets to interface with the OpenAI API.
- `./front-end/`: A custom vanilla JavaScript front-end app providing voice, text, and function calling. (This is a refactored version of the app built in the WebRTC course.)
- `./generic-frontend/`: A generic Next.js app for demonstrating the Realtime API text and voice capabilities.
- `./relay-server-prototype/`: __For reference purposes only.__ The Relay Server presented in a less split-up way which some will find easier to read. 

## Installing and running

Full instructions on how to install and run the different components are found in the `README.md` files under each folder. Here is a quick rundown:

> NOTE:
> You need a separate Terminal for the Relay Server and the front-end projects. They need to run simultaneously to work.

1. Open the repo in GitHub Codespaces
2. Create a `.env` file in the `./relay-server/` folder for your OpenAI API key:
```bash
OPENAI_API_KEY=your-api-key
```
3. From terminal, start the Relay Server:
```bash
cd relay-server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```
4. Open "Ports" and change the Privacy setting for `relay-server` to "Public"
5. Under "Ports", copy the URI for `relay-server`
6. Configure `front-end`:
   - Open `./front-end/js/config`
   - Paste in just the hostname in the `uri` property
   - Change the `protocol` property to `wss://`
7. Run `front-end` from a new terminal window:
```bash
cd front-end
npm run start
```
8. To configure `generic-frontend`:
   - Open `./generic-frontend/src/config.ts`
   - Paste in just the hostname in the `uri` property
   - Change the `protocol` property to `wss://`
9. Run `generic-frontend` from a new terminal window:
```bash
cd generic-frontend
npm run dev
```

## Instructor

Morten Rand-Hendriksen

Principal Staff Instructor, Speaker, Web Designer, and Software Developer

                            

Check out my other courses on [LinkedIn Learning](https://www.linkedin.com/learning/instructors/morten-rand-hendriksen?u=104).

[0]: # (Replace these placeholder URLs with actual course URLs)

[lil-course-url]: https://www.linkedin.com/learning/openai-api-realtime-api-on-the-server-asi
[lil-thumbnail-url]: https://media.licdn.com/dms/image/v2/D4D0DAQHb7sYWKqTUMQ/learning-public-crop_675_1200/B4DZUGYTrnGkAY-/0/1739568790919?e=2147483647&v=beta&t=EzObRg3eNzRbPvsMAKbYmLa1J5zJf1djtCRo7y2BLok
