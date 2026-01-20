TWILIO_ACCOUNT_SID = "ACd875f9348db0cb7683dd065d70dadd7a"
TWILIO_AUTH_TOKEN = "e243075f927bb04bbeedde2643300de9"
TWILIO_PHONE_NUMBER = "+1775 363 9210"
USER_PHONE_NUMBER = "+919193174378"

GROQ_API_KEY = "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"
ELEVEN_API_KEY = "ap2_3842f815-a11d-4ff0-8754-4b2db5c5ae3a"
ELEVEN_VOICE_ID = "en-US-natalie"

# For local development, use localhost
# For production, use ngrok tunnel
BASE_URL = "http://localhost:8001" 

TTS_MODEL = "fast"  
TTS_SPEED = 1.2   
TTS_VOLUME = 1.0    

# Audio Processing Settings
SILENCE_THRESHOLD_MS = 350  
MIN_AUDIO_LENGTH_MS = 300   

CHUNK_DURATION_MS = 20
SILENT_CHUNKS_TO_TRIGGER = SILENCE_THRESHOLD_MS // CHUNK_DURATION_MS  # Now 25 chunks instead of 100

# Voice Activity Detection (VAD) settings
SILENCE_RATIO_THRESHOLD = 0.75  # More sensitive to voice (was 0.8)
MIN_VOICE_CHUNKS = 5    
