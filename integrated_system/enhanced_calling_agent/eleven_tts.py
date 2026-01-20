import requests
from config import ELEVEN_API_KEY, ELEVEN_VOICE_ID

def text_to_speech(text, output_path="response.mp3"):
    """Converts text to speech using ElevenLabs API and handles errors."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(response.content)
        
        print(f" TTS audio successfully saved to {output_path}")
        return output_path

    except requests.exceptions.HTTPError as err:
        print(f"ElevenLabs API Error: {err}")
        print(f"API Response: {response.text}")
        return None 
    except Exception as e:
        print(f"An unexpected error occurred in text_to_speech: {e}")
        return None