import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("API_DEBUG", "true").lower() == "true",
        log_level="info"
    )