import os
import time
import subprocess
import requests
from urllib.parse import quote
import tempfile
from utils import mp3_to_wav

def text_to_speech_edge(text, output_path="response.wav"):
    """
    Use Microsoft Edge TTS as primary - much more reliable than gTTS
    """
    try:
        if not text or not text.strip():
            print("❌ No text provided for TTS")
            return None
            
        # Clean and prepare text
        text = text.strip()[:500]  # Limit length
        
        print(f"🎤 Edge TTS for: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        # Use edge-tts (much more reliable)
        temp_mp3 = f"edge_temp_{int(time.time())}.mp3"
        
        try:
            # Install edge-tts if not available
            subprocess.run(['pip', 'install', 'edge-tts'], 
                         capture_output=True, check=False)
            
            # Generate speech using edge-tts
            cmd = [
                'edge-tts',
                '--voice', 'en-US-AriaNeural',
                '--text', text,
                '--write-media', temp_mp3
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and os.path.exists(temp_mp3):
                # Convert to WAV
                wav_result = mp3_to_wav(temp_mp3, output_path)
                
                # Cleanup
                try:
                    os.remove(temp_mp3)
                except:
                    pass
                    
                if wav_result:
                    print(f"✅ Edge TTS successful: {output_path}")
                    return output_path
                    
        except Exception as e:
            print(f"❌ Edge TTS failed: {e}")
            
        # Cleanup on failure
        try:
            if os.path.exists(temp_mp3):
                os.remove(temp_mp3)
        except:
            pass
            
        return None
        
    except Exception as e:
        print(f"❌ Edge TTS error: {e}")
        return None

def text_to_speech_gtts_robust(text, output_path="response.wav"):
    """
    Robust gTTS implementation with proper error handling and timeouts
    """
    try:
        # Import here to catch import errors
        from gtts import gTTS
        import requests.exceptions
        
        if not text or not text.strip():
            print("❌ No text provided for TTS")
            return None
            
        # Clean and limit text
        text = text.strip()[:300]  # Shorter for reliability
        if not text:
            return None
            
        print(f"🎤 Robust gTTS for: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        temp_mp3 = f"gtts_temp_{int(time.time())}.mp3"
        
        try:
            # Create gTTS object with proper parameters
            tts = gTTS(
                text=text,
                lang='en',
                slow=False,
                lang_check=False,  # Skip language check for speed
                tld='com'
            )
            
            # Save with timeout handling
            start_time = time.time()
            tts.save(temp_mp3)
            generation_time = time.time() - start_time
            
            print(f"⚡ gTTS generation: {generation_time:.2f}s")
            
            # Verify file
            if not os.path.exists(temp_mp3) or os.path.getsize(temp_mp3) < 100:
                print("❌ gTTS generated invalid file")
                return None
                
            # Convert to WAV
            wav_result = mp3_to_wav(temp_mp3, output_path)
            
            # Cleanup
            try:
                os.remove(temp_mp3)
            except:
                pass
                
            if wav_result:
                print(f"✅ gTTS successful: {output_path}")
                return output_path
                
        except (requests.exceptions.RequestException, 
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            print(f"❌ gTTS network error: {e}")
            
        except Exception as e:
            print(f"❌ gTTS error: {e}")
            
        # Cleanup on failure
        try:
            if os.path.exists(temp_mp3):
                os.remove(temp_mp3)
        except:
            pass
            
        return None
        
    except ImportError:
        print("❌ gTTS not installed or import failed")
        return None
    except Exception as e:
        print(f"❌ gTTS robust error: {e}")
        return None

def text_to_speech_espeak(text, output_path="response.wav"):
    """
    Fallback using espeak (offline, always works)
    """
    try:
        if not text or not text.strip():
            return None
            
        text = text.strip()[:500]
        print(f"🎤 eSpeak fallback for: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        # Try espeak command
        cmd = [
            'espeak',
            '-s', '160',  # Speed
            '-v', 'en',   # Voice
            '-w', output_path,  # Write to file
            text
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        
        if result.returncode == 0 and os.path.exists(output_path):
            print(f"✅ eSpeak successful: {output_path}")
            return output_path
            
    except Exception as e:
        print(f"❌ eSpeak error: {e}")
        
    return None

def text_to_speech_festival(text, output_path="response.wav"):
    """
    Another fallback using Festival TTS
    """
    try:
        if not text or not text.strip():
            return None
            
        text = text.strip()[:500]
        print(f"🎤 Festival fallback for: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        # Create temp text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(text)
            temp_txt = f.name
            
        try:
            # Festival command
            cmd = f'echo "{text}" | festival --tts --otype wav > {output_path}'
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
            
            if result.returncode == 0 and os.path.exists(output_path):
                print(f"✅ Festival successful: {output_path}")
                return output_path
                
        finally:
            try:
                os.remove(temp_txt)
            except:
                pass
                
    except Exception as e:
        print(f"❌ Festival error: {e}")
        
    return None

def text_to_speech(text, output_path="response.wav"):
    """
    Main TTS function with multiple fallbacks for maximum reliability
    """
    if not text or not text.strip():
        print("❌ No text provided for TTS")
        return None
        
    start_time = time.time()
    print(f"🚀 Starting TTS for: '{text[:100]}{'...' if len(text) > 100 else ''}'")
    
    # Clean up any existing file
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
        except:
            pass
    
    # Try methods in order of preference
    methods = [
        ("Edge TTS", text_to_speech_edge),
        ("Robust gTTS", text_to_speech_gtts_robust),
        ("eSpeak", text_to_speech_espeak),
        ("Festival", text_to_speech_festival)
    ]
    
    for method_name, method_func in methods:
        try:
            print(f"🔄 Trying {method_name}...")
            result = method_func(text, output_path)
            
            if result and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                if file_size > 1000:  # Reasonable file size
                    total_time = time.time() - start_time
                    print(f"✅ SUCCESS with {method_name}! Time: {total_time:.2f}s, Size: {file_size} bytes")
                    return output_path
                else:
                    print(f"⚠️ {method_name} created file too small: {file_size} bytes")
                    
        except Exception as e:
            print(f"❌ {method_name} failed: {e}")
            continue
    
    # Last resort - create a beep sound
    print("❌ All TTS methods failed - creating error beep")
    try:
        return create_error_beep(output_path)
    except:
        print("❌ Even error beep failed")
        return None

def create_error_beep(output_path="response.wav"):
    """
    Create a simple beep sound as last resort
    """
    try:
        # Use ffmpeg to create a beep
        cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', 
            'sine=frequency=800:duration=1',
            '-ar', '8000', '-ac', '1',
            '-y', output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=5)
        
        if result.returncode == 0 and os.path.exists(output_path):
            print(f"🔔 Error beep created: {output_path}")
            return output_path
            
    except Exception as e:
        print(f"❌ Error beep creation failed: {e}")
        
    return None

# Compatibility aliases
text_to_speech_fast = text_to_speech
text_to_speech_ultra_fast = text_to_speech

def test_tts_methods():
    """
    Test all available TTS methods
    """
    test_text = "Hello, this is a test of the text to speech system."
    results = {}
    
    methods = [
        ("Edge TTS", text_to_speech_edge),
        ("gTTS", text_to_speech_gtts_robust),
        ("eSpeak", text_to_speech_espeak),
        ("Festival", text_to_speech_festival)
    ]
    
    for method_name, method_func in methods:
        print(f"\n🧪 Testing {method_name}...")
        test_file = f"test_{method_name.lower().replace(' ', '_')}.wav"
        
        try:
            start_time = time.time()
            result = method_func(test_text, test_file)
            test_time = time.time() - start_time
            
            if result and os.path.exists(test_file):
                file_size = os.path.getsize(test_file)
                results[method_name] = {
                    "success": True,
                    "time": test_time,
                    "file_size": file_size
                }
                print(f"✅ {method_name}: SUCCESS ({test_time:.2f}s, {file_size} bytes)")
                
                # Cleanup test file
                try:
                    os.remove(test_file)
                except:
                    pass
            else:
                results[method_name] = {"success": False, "time": test_time}
                print(f"❌ {method_name}: FAILED ({test_time:.2f}s)")
                
        except Exception as e:
            results[method_name] = {"success": False, "error": str(e)}
            print(f"❌ {method_name}: ERROR - {e}")
    
    return results

if __name__ == "__main__":
    # Test when run directly
    print("🧪 Testing TTS methods...")
    results = test_tts_methods()
    
    print("\n📊 Test Results:")
    for method, result in results.items():
        status = "✅ WORKING" if result.get("success") else "❌ FAILED"
        print(f"  {method}: {status}")
        
    print("\n🚀 Testing main TTS function...")
    test_result = text_to_speech("This is the main TTS test.", "main_test.wav")
    if test_result:
        print("✅ Main TTS function working!")
        try:
            os.remove("main_test.wav")
        except:
            pass
    else:
        print("❌ Main TTS function failed!")