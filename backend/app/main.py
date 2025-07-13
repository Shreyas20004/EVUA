# main.py - Simple FastAPI Hello World server
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timezone

# Initialize FastAPI app
app = FastAPI(
    title="Hello World API",
    description="A simple Hello World FastAPI server",
    version="1.0.0",
)

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your React app's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class Message(BaseModel):
    message: str
    timestamp: str

class HealthCheck(BaseModel):
    status: str
    timestamp: str

# API endpoints
@app.get("/")
def root():
    """Root endpoint - Hello World"""
    return {
        "message": "Hello World from FastAPI!",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/hello")
def hello():
    """Simple hello endpoint"""
    return {
        "message": "Hello from the FastAPI server!",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health", response_model=HealthCheck)
def health_check():
    """Check API health"""
    return {
        "status": "OK",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/echo", response_model=Message)
def echo(message: Message):
    """Echo back the received message"""
    return {
        "message": f"Echo: {message.message}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }