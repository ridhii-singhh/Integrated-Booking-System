from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from endpoints import router

# Create FastAPI app
app = FastAPI(
    title="Booking Agent API",
    description="API for booking meetings using natural language commands",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router
app.include_router(router, prefix="/api/v1", tags=["booking"])

@app.get("/")
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": "Booking Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "book_meeting": "/api/v1/book",
            "confirm_booking": "/api/v1/confirm",
            "reschedule_preview": "/api/v1/reschedule",
            "reschedule_confirm": "/api/v1/reschedule/confirm",
            "cancel_preview": "/api/v1/cancel",
            "cancel_confirm": "/api/v1/cancel/confirm",
            "health": "/api/v1/health"
        },
        "example": {
            "command": "book a progress meeting with tejalr2125@gmail.com on next tuesday 5.00 pm for 30 mins"
        }
    }

# Run the server directly when this file is executed
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    ) 