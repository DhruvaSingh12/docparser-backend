from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from app.api.v1 import router as v1_router
from app.db import init_db

# Load environment variables
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Starting DocParse API...")
    init_db()
    print("Database initialized.")
    yield
    # Shutdown
    print("Shutting down DocParse API...")

# Create FastAPI app
app = FastAPI(
    title=os.getenv("APP_NAME", "DocParse API"),
    description="AI-powered medical document parsing for CGHS compliance",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for mobile app integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(v1_router, prefix="/api/v1", tags=["Document Processing"])

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "DocParse API is running",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "timestamp": "2025-09-21T00:00:00Z"
    }
