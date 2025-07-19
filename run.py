import uvicorn
import os

if __name__ == "__main__":
    # Production configuration
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        workers=1      # Single worker for simple logging
    )