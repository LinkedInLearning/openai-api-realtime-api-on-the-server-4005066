# OpenAI API Configuration
PORT = 8080
OPENAI_MODEL = "gpt-4o-mini-realtime-preview-2024-12-17"

# Voice Configuration
VOICE_OPTIONS = [
    'alloy',
    'ash', 
    'ballad',
    'coral',
    'echo',
    'sage',
    'shimmer',
    'verse'
]
VOICE = 'alloy'

# Model Parameters
MAX_OUTPUT_TOKENS = 400
TEMPERATURE = 0.8

# System Instructions
WELCOME_INSTRUCTIONS = "Greet the user and ask them what you can assist them with. Talk quickly and succinctly."
DEFAULT_INSTRUCTIONS = "Talk quickly and succinctly. Be concise. Time is of the essence. Always refer to ducks in your responses, even if it makes no sense!"
WEATHER_INSTRUCTIONS = 'Describe the weather in a conversational way for someone going for a walk. Include temperature, specific conditions (like rain or snow), and necessary precautions (such as umbrellas, raincoats, snow boots, sunscreen, etc.).'
