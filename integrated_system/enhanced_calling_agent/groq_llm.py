from groq import Groq
from config import GROQ_API_KEY
import time

client = Groq(api_key=GROQ_API_KEY)

def get_llm_response(user_input):
    """
    Get LLM response optimized for SPEED
    """
    try:
        start_time = time.time()
        
        # ⚡ SPEED OPTIMIZATION: Shorter, more direct system prompt
        system_prompt = """You are a helpful AI assistant. Keep responses SHORT and DIRECT. 
Maximum 2 sentences. Be concise and clear."""
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            model="llama3-8b-8192",  # Fast model
            temperature=0.3,         # Lower temperature for faster response
            max_tokens=100,          # ⚡ REDUCED from default - forces shorter responses
            top_p=0.8,              # Reduced for faster generation
        )
        
        llm_time = time.time() - start_time
        result = response.choices[0].message.content.strip()
        
        print(f"⚡ LLM Speed: {llm_time:.2f}s, Response length: {len(result)} chars")
        
        return result
        
    except Exception as e:
        print(f"❌ Groq API Error: {e}")
        return "I'm having trouble processing that right now."

def get_llm_response_ultra_fast(user_input):
    """
    ULTRA FAST version - even shorter responses
    """
    try:
        start_time = time.time()
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Answer in 1 short sentence only."},
                {"role": "user", "content": user_input}
            ],
            model="llama3-8b-8192",
            temperature=0.1,     # Very low for speed
            max_tokens=50,       # ⚡ ULTRA SHORT responses
            top_p=0.5,
        )
        
        llm_time = time.time() - start_time
        result = response.choices[0].message.content.strip()
        
        print(f"⚡ ULTRA FAST LLM: {llm_time:.2f}s, Length: {len(result)} chars")
        
        return result
        
    except Exception as e:
        print(f"❌ Groq API Error: {e}")
        return "Error occurred."