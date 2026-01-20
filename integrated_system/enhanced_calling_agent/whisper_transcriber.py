from faster_whisper import WhisperModel

model = WhisperModel("base")

def transcribe_audio(audio_path):
    segments, _ = model.transcribe(audio_path)
    return " ".join([seg.text for seg in segments])
