import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db.database import engine, Base
import app.models  # Ensure models registered

# Initialize Database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered Receipt & Invoice Document Intelligence platform with grounded RAG",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount upload directory for file serving
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include Routers
from app.api import auth, receipts, chat, search, analytics

app.include_router(auth.router)
app.include_router(receipts.router)
app.include_router(chat.router)
app.include_router(search.router)
app.include_router(analytics.router)

@app.get("/")
def read_root():
    return {
        "app": settings.APP_NAME,
        "status": "online",
        "message": "ReceiptRAG API Server is running."
    }

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}
