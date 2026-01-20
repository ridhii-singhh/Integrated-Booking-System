import os
import torch
from TTS.api import TTS
import tempfile

class CoquiTTSEngine:
    def __init__(self): 
        self.tts = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔊 Initializing Coqui TTS on device: {self.device}")
        self._initialize_tts()
    
    def _initialize_tts(self):
        """Initialize TTS model - using a fast, high-quality English model"""
        try:
            model_name = "tts_models/en/ljspeech/fast_pitch"
            
            print(f"📥 Loading TTS model: {model_name}")
            self.tts = TTS(model_name=model_name).to(self.device)
            print(" Coqui TTS initialized successfully!")
            
        except Exception as e:
            print(f" Error initializing primary model, trying backup: {e}")
            try:
                backup_model = "tts_models/en/ljspeech/tacotron2-DDC"
                print(f" Loading backup TTS model: {backup_model}")
                self.tts = TTS(model_name=backup_model).to(self.device)
                print(" Backup Coqui TTS initialized successfully!")
            except Exception as e2:
                print(f" Error initializing backup model: {e2}")
                try:
                    self.tts = TTS(model_name="tts_models/en/ljspeech/glow-tts").to(self.device)
                    print("Fallback Coqui TTS initialized!")
                except Exception as e3:
                    print(f"All TTS models failed: {e3}")
                    raise e3

_tts_engine = None

def get_tts_engine():
    """Get or create the global TTS engine instance"""
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = CoquiTTSEngine()
    return _tts_engine

def text_to_speech(text, output_path="response.wav"):
    """
    Convert text to speech using Coqui TTS
    
    Args:
        text (str): Text to convert to speech
        output_path (str): Path where to save the audio file
    
    Returns:
        str: Path to the generated audio file, or None if failed
    """
    try:
        if not text or not text.strip():
            print("Empty text provided to TTS")
            return None
            
        cleaned_text = clean_text_for_tts(text)
        print(f"🗣️ Converting to speech: '{cleaned_text[:50]}{'...' if len(cleaned_text) > 50 else ''}'")
        
        engine = get_tts_engine()
        if not engine.tts:
            print("❌ TTS engine not initialized")
            return None
        
        # Note: Coqui TTS outputs WAV directly, so we can skip MP3 conversion
        if output_path.endswith('.mp3'):
            # Change extension to .wav since Coqui outputs WAV
            output_path = output_path.replace('.mp3', '.wav')
        
        engine.tts.tts_to_file(
            text=cleaned_text,
            file_path=output_path
        )
        
        # Verify the file was created
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            print(f"✅ TTS audio successfully saved to {output_path}")
            return output_path
        else:
            print(f"❌ TTS failed - output file is empty or doesn't exist")
            return None
            
    except Exception as e:
        print(f"❌ Error in Coqui TTS: {e}")
        import traceback
        traceback.print_exc()
        return None

def clean_text_for_tts(text):
    """
    Clean text for better TTS pronunciation
    """
    import re
    
    # Remove or replace problematic characters
    text = re.sub(r'[^\w\s.,!?;:\-\'"()]', ' ', text)
    
    # Fix common abbreviations
    replacements = {
        r'\bDr\.': 'Doctor',
        r'\bMr\.': 'Mister', 
        r'\bMrs\.': 'Missus',
        r'\bMs\.': 'Miss',
        r'\betc\.': 'etcetera',
        r'\be\.g\.': 'for example',
        r'\bi\.e\.': 'that is',
        r'\bvs\.': 'versus',
        r'\bUSA\b': 'United States of America',
        r'\bUK\b': 'United Kingdom',
        r'\bAI\b': 'Artificial Intelligence',
        r'\bAPI\b': 'A P I',
        r'\bURL\b': 'U R L',
        r'\bHTTP\b': 'H T T P',
    }
    
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Clean up extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Ensure text ends with punctuation for natural speech
    if text and text[-1] not in '.!?':
        text += '.'
    
    return text

def test_coqui_tts():
    """Test function for Coqui TTS"""
    test_text = "Hello! This is a test of the Coqui text to speech system. It should sound natural and clear."
    
    print("Testing Coqui TTS...")
    result = text_to_speech(test_text, "coqui_test.wav")
    
    if result:
        print(f" Test successful! Audio saved to: {result}")
        print(f" File size: {os.path.getsize(result)} bytes")
        return True
    else:
        print("❌ Test failed!")
        return False

# Alternative voices and models available in Coqui TTS
AVAILABLE_MODELS = {
    "fast": "tts_models/en/ljspeech/fast_pitch",  # Fast generation
    "quality": "tts_models/en/ljspeech/tacotron2-DDC",  # Higher quality
    "neural": "tts_models/en/ljspeech/glow-tts",  # Neural vocoder
    "multi": "tts_models/multilingual/multi-dataset/your_tts",  # Multilingual
}

def switch_tts_model(model_key="fast"):
    """
    Switch to a different TTS model
    
    Args:
        model_key (str): Key from AVAILABLE_MODELS
    """
    global _tts_engine
    
    if model_key not in AVAILABLE_MODELS:
        print(f"Unknown model key: {model_key}")
        print(f"Available models: {list(AVAILABLE_MODELS.keys())}")
        return False
    
    try:
        print(f" Switching to TTS model: {model_key}")
        model_name = AVAILABLE_MODELS[model_key]
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        new_tts = TTS(model_name=model_name).to(device)
        
        if _tts_engine:
            _tts_engine.tts = new_tts
        else:
            _tts_engine = CoquiTTSEngine()
            _tts_engine.tts = new_tts
        
        print(f" Successfully switched to {model_key} model")
        return True
        
    except Exception as e:
        print(f" Error switching TTS model: {e}")
        return False

if __name__ == "__main__":
    test_coqui_tts()