from sqlalchemy import create_engine, exc, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import logging
import time
import os
from contextlib import contextmanager

from app.core.config import DATABASE_URL
from app.core.supabase_client import supabase

# Configure logging
logger = logging.getLogger(__name__)

# Create a Base class for declarative models
Base = declarative_base()

# For SQLAlchemy compatibility with existing code
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Add retry logic for database connection
def get_engine(retries=5, delay=2):
    """
    Create a database engine with retry logic for more resilient connections.
    This is used as a fallback for local development if Supabase is not available.
    """
    for attempt in range(retries):
        try:
            logger.info(f"Attempting to connect to database (attempt {attempt+1}/{retries})")
            # Create SQLAlchemy engine with connection pooling
            engine = create_engine(
                DATABASE_URL,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
                connect_args={"connect_timeout": 10},  # Add connection timeout
            )

            # Test the connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("Database connection successful")
                return engine
        except exc.SQLAlchemyError as e:
            logger.error(f"Database connection failed: {str(e)}")
            if attempt < retries - 1:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error("All database connection attempts failed")
                # In production, we'll continue with the engine even if the test failed
                # This allows the application to start and retry connections later
                if os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production":
                    logger.warning("Creating engine anyway since we're in production")
                    return create_engine(
                        DATABASE_URL,
                        poolclass=QueuePool,
                        pool_size=5,
                        max_overflow=10,
                        pool_timeout=30,
                        pool_recycle=1800,
                        connect_args={"connect_timeout": 10},
                    )
                raise

# Get the engine with retry logic (for SQLAlchemy compatibility)
engine = get_engine()

# Create a SessionLocal class for database sessions (for SQLAlchemy compatibility)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get DB session
def get_db():
    """
    Dependency function to get a database session.
    Yields a database session and ensures it's closed after use.
    This is kept for compatibility with existing code.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Supabase helper functions
def get_table(table_name):
    """
    Get a Supabase table reference.
    """
    return supabase.table(table_name)

@contextmanager
def supabase_transaction():
    """
    A context manager for Supabase transactions.
    This is a simple implementation as Supabase doesn't have built-in transaction support.
    """
    try:
        yield supabase
    except Exception as e:
        logger.error(f"Error in Supabase transaction: {str(e)}")
        raise
