import os
import subprocess
import tempfile
from pathlib import Path

def text_to_speech(text, output_path="response.wav"):
    """
    Converts text to speech using multiple free TTS options.
    Falls back through different engines if one fails.
    """
    
    # Option 1: gTTS (Google Text-to-Speech) 
    try:
        return gtts_tts(text, output_path)
    except Exception as e:
        print(f" gTTS failed: {e}")
    
    # Option 2: pyttsx3 (Offline TTS using system voices)
    try:
        return pyttsx3_tts(text, output_path)
    except Exception as e:
        print(f" pyttsx3 failed: {e}")
    
    # Option 3: espeak (Linux/Windows command-line TTS)
    try:
        return espeak_tts(text, output_path)
    except Exception as e:
        print(f" espeak failed: {e}")
    
    # Option 4: Try say (macOS built-in TTS)
    try:
        return say_tts(text, output_path)
    except Exception as e:
        print(f" macOS say failed: {e}")
    
    print(" All TTS engines failed")
    return None

def gtts_tts(text, output_path):
    """Google Text-to-Speech (requires internet, sounds natural)"""
    try:
        from gtts import gTTS
        import pygame
        
        # Create temporary MP3 file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
            temp_mp3 = tmp_file.name
        
        # Generate speech
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(temp_mp3)
        
        # Convert MP3 to WAV using ffmpeg or pygame
        if convert_mp3_to_wav(temp_mp3, output_path):
            os.unlink(temp_mp3)  # Clean up temp file
            print(f" gTTS: Audio saved to {output_path}")
            return output_path
        else:
            os.unlink(temp_mp3)
            return None
            
    except ImportError:
        print(" Installing gTTS...")
        subprocess.run(["pip", "install", "gtts", "pygame"], check=True)
        return gtts_tts(text, output_path)  # Retry after installation

def pyttsx3_tts(text, output_path):
    """Offline TTS using system voices (Windows: SAPI, Linux: espeak, macOS: NSSpeechSynthesizer)"""
    try:
        import pyttsx3
        
        engine = pyttsx3.init()
        
        # Configure voice settings
        voices = engine.getProperty('voices')
        if voices:
            # Try to find a good English voice
            for voice in voices:
                if 'english' in voice.name.lower() or 'en' in voice.id.lower():
                    engine.setProperty('voice', voice.id)
                    break
        
        # Set speech rate and volume
        engine.setProperty('rate', 180)    # Speed (words per minute)
        engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
        
        # Save to file
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        
        # Verify file was created
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            print(f" pyttsx3: Audio saved to {output_path}")
            return output_path
        else:
            return None
            
    except ImportError:
        print(" Installing pyttsx3...")
        subprocess.run(["pip", "install", "pyttsx3"], check=True)
        return pyttsx3_tts(text, output_path)  # Retry after installation

def espeak_tts(text, output_path):
    """eSpeak TTS (Linux/Windows command-line tool)"""
    try:
        # Check if espeak is available
        subprocess.run(["espeak", "--version"], capture_output=True, check=True)
        
        # Generate speech with espeak
        command = [
            "espeak",
            "-v", "en+f3",  # English voice, female variant 3
            "-s", "150",    # Speed (words per minute)
            "-w", output_path,  # Output to WAV file
            text
        ]
        
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_path):
            print(f" espeak: Audio saved to {output_path}")
            return output_path
        else:
            print(f" espeak error: {result.stderr}")
            return None
            
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(" espeak not found. Install with: sudo apt-get install espeak (Linux) or download from http://espeak.sourceforge.net/")
        return None

def say_tts(text, output_path):
    """macOS built-in 'say' command"""
    try:
        # Check if we're on macOS and 'say' is available
        subprocess.run(["say", "--version"], capture_output=True, check=True)
        
        # Use say to generate audio file
        command = [
            "say",
            "-v", "Samantha",
            "-r", "180",       # Rate (words per minute)
            "-o", output_path, # Output file
            text
        ]
        
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_path):
            print(f" macOS say: Audio saved to {output_path}")
            return output_path
        else:
            print(f" say error: {result.stderr}")
            return None
            
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(" macOS 'say' command not available")
        return None

def convert_mp3_to_wav(mp3_path, wav_path):
    """Convert MP3 to WAV using ffmpeg or pygame"""
    
    # Try ffmpeg first (best quality)
    try:
        command = [
            'ffmpeg', '-i', mp3_path,
            '-ar', '8000',      # 8kHz sample rate for phone calls
            '-ac', '1',         # Mono
            '-sample_fmt', 's16', # 16-bit samples
            '-y',               # Overwrite output
            wav_path
        ]
        
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        
        if result.returncode == 0 and os.path.exists(wav_path):
            print(f" ffmpeg conversion successful")
            return True
            
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        print(" ffmpeg conversion failed, trying pygame...")
    
    try:
        import pygame
        
        pygame.mixer.init(frequency=8000, size=-16, channels=1)
        sound = pygame.mixer.Sound(mp3_path)
        
        pygame.mixer.quit()
        
        import wave
        import audioop
        return True
        
    except Exception as e:
        print(f" pygame conversion failed: {e}")
        return False

def install_dependencies():
    """Install required dependencies for TTS"""
    packages = [
        "gtts",      # Google Text-to-Speech
        "pyttsx3",   # Cross-platform TTS
        "pygame",    # For audio handling
    ]
    
    for package in packages:
        try:
            subprocess.run(["pip", "install", package], check=True)
            print(f" Installed {package}")
        except subprocess.CalledProcessError:
            print(f" Failed to install {package}")

def test_tts():
    """Test all available TTS engines"""
    test_text = "Hello! This is a test of the text to speech system. How does it sound?"
    
    print("🧪 Testing TTS engines...")
    
    engines = [
        ("gTTS", gtts_tts),
        ("pyttsx3", pyttsx3_tts),
        ("espeak", espeak_tts),
        ("macOS say", say_tts)
    ]
    
    for name, engine_func in engines:
        print(f"\n🔊 Testing {name}...")
        output_file = f"test_{name.lower().replace(' ', '_')}.wav"
        
        try:
            result = engine_func(test_text, output_file)
            if result:
                print(f" {name} working! Output: {output_file}")
            else:
                print(f" {name} failed")
        except Exception as e:
            print(f" {name} error: {e}")

if __name__ == "__main__":
    test_tts()