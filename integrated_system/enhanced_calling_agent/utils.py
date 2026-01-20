import wave
import subprocess
import os
import struct
from twilio.rest import Client
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, BASE_URL

# Simple μ-law to linear conversion (replacement for audioop)
def ulaw2lin(ulaw_data, width):
    """Convert μ-law encoded audio to linear PCM"""
    if width != 2:
        raise ValueError("Only 16-bit output supported")
    
    # μ-law decoding table
    MULAW_DECODE_TABLE = [
        -32124, -31100, -30076, -29052, -28028, -27004, -25980, -24956,
        -23932, -22908, -21884, -20860, -19836, -18812, -17788, -16764,
        -15996, -15484, -14972, -14460, -13948, -13436, -12924, -12412,
        -11900, -11388, -10876, -10364, -9852, -9340, -8828, -8316,
        -7932, -7676, -7420, -7164, -6908, -6652, -6396, -6140,
        -5884, -5628, -5372, -5116, -4860, -4604, -4348, -4092,
        -3900, -3772, -3644, -3516, -3388, -3260, -3132, -3004,
        -2876, -2748, -2620, -2492, -2364, -2236, -2108, -1980,
        -1884, -1820, -1756, -1692, -1628, -1564, -1500, -1436,
        -1372, -1308, -1244, -1180, -1116, -1052, -988, -924,
        -876, -844, -812, -780, -748, -716, -684, -652,
        -620, -588, -556, -524, -492, -460, -428, -396,
        -372, -356, -340, -324, -308, -292, -276, -260,
        -244, -228, -212, -196, -180, -164, -148, -132,
        -120, -112, -104, -96, -88, -80, -72, -64,
        -56, -48, -40, -32, -24, -16, -8, 0,
        32124, 31100, 30076, 29052, 28028, 27004, 25980, 24956,
        23932, 22908, 21884, 20860, 19836, 18812, 17788, 16764,
        15996, 15484, 14972, 14460, 13948, 13436, 12924, 12412,
        11900, 11388, 10876, 10364, 9852, 9340, 8828, 8316,
        7932, 7676, 7420, 7164, 6908, 6652, 6396, 6140,
        5884, 5628, 5372, 5116, 4860, 4604, 4348, 4092,
        3900, 3772, 3644, 3516, 3388, 3260, 3132, 3004,
        2876, 2748, 2620, 2492, 2364, 2236, 2108, 1980,
        1884, 1820, 1756, 1692, 1628, 1564, 1500, 1436,
        1372, 1308, 1244, 1180, 1116, 1052, 988, 924,
        876, 844, 812, 780, 748, 716, 684, 652,
        620, 588, 556, 524, 492, 460, 428, 396,
        372, 356, 340, 324, 308, 292, 276, 260,
        244, 228, 212, 196, 180, 164, 148, 132,
        120, 112, 104, 96, 88, 80, 72, 64,
        56, 48, 40, 32, 24, 16, 8, 0
    ]
    
    linear_data = bytearray()
    for byte in ulaw_data:
        if isinstance(byte, int):
            sample = MULAW_DECODE_TABLE[byte & 0xFF]
        else:
            sample = MULAW_DECODE_TABLE[ord(byte) & 0xFF]
        linear_data.extend(struct.pack('<h', sample))
    
    return bytes(linear_data)

def save_ulaw_as_wav(ulaw_data, output_filename):
    """
    Convert μ-law audio data to WAV format with better error handling
    """
    try:
        if not ulaw_data or len(ulaw_data) < 160: 
            print(f" Audio data too small: {len(ulaw_data) if ulaw_data else 0} bytes")
            return False
            
        try:
            linear_data = ulaw2lin(ulaw_data, 2) 
        except Exception as e:
            print(f" Error converting μ-law to linear: {e}")
            return False
        
        # Create WAV file
        with wave.open(output_filename, 'wb') as wav_file:
            wav_file.setnchannels(1)      
            wav_file.setsampwidth(2)      
            wav_file.setframerate(8000)  
            wav_file.writeframes(linear_data)
            
 
        if os.path.exists(output_filename):
            file_size = os.path.getsize(output_filename)
            duration = len(linear_data) / (2 * 8000)  
            print(f" WAV file created: {output_filename} ({file_size} bytes, {duration:.2f}s)")
            return True
        else:
            print(f" Failed to create WAV file: {output_filename}")
            return False
            
    except Exception as e:
        print(f" Error in save_ulaw_as_wav: {e}")
        return False

def mp3_to_wav(mp3_path, wav_path):
    """
    Convert MP3 to WAV using ffmpeg with better error handling
    """
    try:
        if not os.path.exists(mp3_path):
            print(f" MP3 file not found: {mp3_path}")
            return None
            
        if os.path.exists(wav_path):
            os.remove(wav_path)
            
        command = [
            'ffmpeg', '-i', mp3_path,
            '-ar', '8000',      
            '-ac', '1',         
            '-sample_fmt', 's16', 
            '-y',               
            wav_path
        ]
        
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            timeout=20  
        )
        
        if result.returncode != 0:
            print(f" ffmpeg error: {result.stderr}")
            return None
            
        # Verify the output file
        if os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000:
            print(f" MP3 to WAV conversion successful: {wav_path}")
            return wav_path
        else:
            print(f" WAV file creation failed or file too small")
            return None
            
    except subprocess.TimeoutExpired:
        print(" ffmpeg conversion timed out")
        return None
    except FileNotFoundError:
        print(" ffmpeg not found. Please install ffmpeg.")
        return None
    except Exception as e:
        print(f" Error in mp3_to_wav: {e}")
        return None

def redirect_call_to_play(call_sid):
    """
    Redirect the active call to play the response audio with better error handling
    """
    try:
        if not call_sid:
            print(" No call_sid provided for redirect")
            return False
            
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Create TwiML to play the response
        play_url = f"{BASE_URL}/play-response"
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Play>{play_url}</Play>
            <Pause length="1"/>
            <Start>
                <Stream url="wss://{BASE_URL.split('://')[1]}/stream" track="inbound_track" />
            </Start>
            <Pause length="30"/>
        </Response>
        """
        
        # Update the call with new TwiML
        call = client.calls(call_sid).update(
            twiml=twiml.strip()
        )
        
        print(f" Call {call_sid} redirected to play response")
        return True
        
    except Exception as e:
        print(f" Error redirecting call: {e}")
        return False

def validate_audio_file(file_path, min_size=1000):
    """
    Validate that an audio file exists and has reasonable content
    """
    if not os.path.exists(file_path):
        return False, f"File does not exist: {file_path}"
    
    file_size = os.path.getsize(file_path)
    if file_size < min_size:
        return False, f"File too small: {file_size} bytes"
    
    try:
        with wave.open(file_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            sample_rate = wav_file.getframerate()
            duration = frames / sample_rate
            
            if duration < 0.1:  
                return False, f"Audio too short: {duration:.3f}s"
                
            return True, f"Valid audio: {duration:.2f}s, {sample_rate}Hz"
    except Exception as e:
        return False, f"Invalid WAV file: {e}"

def cleanup_temp_files():
    """
    Clean up temporary audio files
    """
    temp_files = ["caller.wav", "response.wav", "test.wav", "coqui_test.wav"]
    for file in temp_files:
        try:
            if os.path.exists(file):
                os.remove(file)
                print(f" Cleaned up: {file}")
        except Exception as e:
            print(f" Error cleaning {file}: {e}")