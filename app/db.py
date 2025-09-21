from sqlmodel import SQLModel, create_engine, Session
import os
import logging
from dotenv import load_dotenv

logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Please configure your Neon database URL in .env file")

DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

engine = create_engine(
    DATABASE_URL,
    echo=DEBUG_MODE,  # Only show SQL queries in debug mode
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,    # Recycle connections every 5 minutes
)

def get_session():
    """Get database session"""
    with Session(engine) as session:
        yield session

def init_db():
    """Initialize database tables"""
    SQLModel.metadata.create_all(engine)
