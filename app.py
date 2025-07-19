from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import json
import os
import logging
from typing import Optional, Dict, Any
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="In-Car Monitoring Backend",
    description="Simple backend for logging AI monitoring summaries",
    version="1.0.0"
)

# Enable CORS for Android app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Android app's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class MonitoringMetadata(BaseModel):
    framesProcessed: int
    peopleDetected: int
    processingTimeSeconds: float
    videoSource: str
    inferenceTimeMs: float
    totalDetections: int

class SummaryLogRequest(BaseModel):
    session_id: str
    summary: str
    metadata: MonitoringMetadata
    timestamp: Optional[str] = None

class SummaryLogResponse(BaseModel):
    status: str
    message: str
    log_id: str
    timestamp: str

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

def get_log_filename():
    """Generate daily log filename"""
    today = datetime.now().strftime("%Y-%m-%d")
    return f"logs/monitoring_logs_{today}.jsonl"

def log_to_file(data: dict):
    """Log data to JSON Lines file with timestamp"""
    try:
        log_filename = get_log_filename()
        
        # Add server timestamp
        data["server_timestamp"] = datetime.now().isoformat()
        
        # Append to JSON Lines file (one JSON object per line)
        with open(log_filename, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")
        
        logger.info(f"Logged summary to {log_filename}")
        return True
    except Exception as e:
        logger.error(f"Failed to log to file: {str(e)}")
        return False

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "In-Car Monitoring Backend is running",
        "timestamp": datetime.now().isoformat(),
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "logs_directory": "logs",
        "current_log_file": get_log_filename()
    }

@app.post("/api/log-summary", response_model=SummaryLogResponse)
async def log_summary(request: SummaryLogRequest):
    """
    Main endpoint to receive and log AI-generated summaries from Android app
    """
    try:
        # Generate unique log ID
        log_id = str(uuid.uuid4())
        
        # Use provided timestamp or generate new one
        timestamp = request.timestamp or datetime.now().isoformat()
        
        # Prepare log data
        log_data = {
            "log_id": log_id,
            "session_id": request.session_id,
            "client_timestamp": request.timestamp,
            "summary": request.summary,
            "metadata": request.metadata.dict(),
            "timestamp": timestamp
        }
        
        # Log to file
        if log_to_file(log_data):
            logger.info(f"Successfully logged summary for session {request.session_id}")
            
            return SummaryLogResponse(
                status="success",
                message="Summary logged successfully",
                log_id=log_id,
                timestamp=timestamp
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to log summary to file")
            
    except Exception as e:
        logger.error(f"Error logging summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/logs/today")
async def get_today_logs():
    """Get today's logs (for debugging/monitoring)"""
    try:
        log_filename = get_log_filename()
        
        if not os.path.exists(log_filename):
            return {"logs": [], "message": "No logs for today"}
        
        logs = []
        with open(log_filename, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
        
        return {
            "logs": logs,
            "count": len(logs),
            "log_file": log_filename
        }
    except Exception as e:
        logger.error(f"Error reading logs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to read logs")

@app.get("/api/stats")
async def get_stats():
    """Get basic statistics from today's logs"""
    try:
        log_filename = get_log_filename()
        
        if not os.path.exists(log_filename):
            return {"message": "No logs for today", "stats": {}}
        
        total_logs = 0
        total_frames = 0
        total_people = 0
        sessions = set()
        
        with open(log_filename, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    log_entry = json.loads(line)
                    total_logs += 1
                    sessions.add(log_entry["session_id"])
                    
                    metadata = log_entry.get("metadata", {})
                    total_frames += metadata.get("frames_processed", 0)
                    total_people += metadata.get("people_detected", 0)
        
        return {
            "stats": {
                "total_logs": total_logs,
                "unique_sessions": len(sessions),
                "total_frames_processed": total_frames,
                "total_people_detected": total_people
            },
            "log_file": log_filename
        }
    except Exception as e:
        logger.error(f"Error calculating stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to calculate stats")

if __name__ == "__main__":
    import uvicorn
    
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    print("Starting In-Car Monitoring Backend...")
    print("API Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code changes (development only)
    )