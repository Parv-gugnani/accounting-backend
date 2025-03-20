from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, exc
import os
import logging
import time
from pathlib import Path

from app.db.database import engine, Base, get_db
from app.core.supabase_client import supabase, SUPABASE_URL
from app.core.config import PROJECT_NAME, VERSION, ALLOWED_ORIGINS, DEBUG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)
logger = logging.getLogger(__name__)

# Create tables with retry logic
def create_tables():
    max_retries = 5
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to create database tables (attempt {attempt+1}/{max_retries})")
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
            return
        except exc.SQLAlchemyError as e:
            logger.error(f"Failed to create tables: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.warning("Could not create tables, but continuing startup")

# Initialize FastAPI app
app = FastAPI(title=PROJECT_NAME, version=VERSION)

# Get Railway environment variables
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
RAILWAY_SERVICE_NAME = os.getenv("RAILWAY_SERVICE_NAME", "")
RAILWAY_ENVIRONMENT_NAME = os.getenv("RAILWAY_ENVIRONMENT_NAME", "")
RAILWAY_PROJECT_NAME = os.getenv("RAILWAY_PROJECT_NAME", "")

# Configure CORS
allowed_origins = ALLOWED_ORIGINS.copy()
if RAILWAY_PUBLIC_DOMAIN:
    allowed_origins.append(f"https://{RAILWAY_PUBLIC_DOMAIN}")
    # Also add with www subdomain
    allowed_origins.append(f"https://www.{RAILWAY_PUBLIC_DOMAIN}")

# Add specific Railway domain
allowed_origins.append("https://accounting-backend-production-4381.up.railway.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# Simple HTML content for fallback
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Accounting Backend</title>
</head>
<body>
    <h1>Welcome to the Accounting Backend</h1>
    <p>The application is running, but there may be issues with the database connection.</p>
    <p>Please check the logs for more information.</p>
</body>
</html>
"""

# Create tables on startup
try:
    create_tables()
except Exception as e:
    logger.error(f"Error during startup: {str(e)}")

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        return HTMLResponse(content=html_content)

@app.get("/health")
def health_check():
    """
    Health check endpoint that checks database and Supabase connections
    """
    health_status = {
        "status": "ok",
        "database": "unknown",
        "supabase": "unknown",
        "static_files": "unknown",
        "templates": "unknown",
        "environment": {
            "debug": DEBUG,
            "allowed_origins": allowed_origins,
            "railway_info": {
                "public_domain": RAILWAY_PUBLIC_DOMAIN,
                "service_name": RAILWAY_SERVICE_NAME,
                "environment_name": RAILWAY_ENVIRONMENT_NAME,
                "project_name": RAILWAY_PROJECT_NAME
            }
        }
    }

    # Check database connection
    try:
        # Use SQLAlchemy to check database connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        health_status["database"] = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        health_status["database"] = "disconnected"
        health_status["status"] = "degraded"

    # Check Supabase connection
    try:
        # Simple check to see if we can access Supabase
        response = supabase.table("_dummy_check").select("*").limit(1).execute()
        health_status["supabase"] = "connected"
    except Exception as e:
        logger.error(f"Supabase health check failed: {str(e)}")
        health_status["supabase"] = "disconnected"
        health_status["status"] = "degraded"

    # Check if static files directory exists
    static_dir = Path("app/static")
    if static_dir.exists() and static_dir.is_dir():
        health_status["static_files"] = "available"
    else:
        logger.error("Static files directory not found")
        health_status["static_files"] = "unavailable"
        health_status["status"] = "degraded"

    # Check if templates directory exists
    templates_dir = Path("app/templates")
    if templates_dir.exists() and templates_dir.is_dir():
        health_status["templates"] = "available"
    else:
        logger.error("Templates directory not found")
        health_status["templates"] = "unavailable"
        health_status["status"] = "degraded"

    # Return appropriate status code
    status_code = 200 if health_status["status"] == "ok" else 503

    return JSONResponse(
        content=health_status,
        status_code=status_code
    )

@app.get("/info")
def get_info():
    """
    Returns information about the application environment
    """
    return {
        "project_name": PROJECT_NAME,
        "version": VERSION,
        "environment": os.getenv("RAILWAY_ENVIRONMENT_NAME", "development"),
        "database_connected": True,  # This will be overridden if there's an error
        "supabase_url": SUPABASE_URL,
        "railway_info": {
            "service": os.getenv("RAILWAY_SERVICE_NAME", "unknown"),
            "environment": os.getenv("RAILWAY_ENVIRONMENT_NAME", "unknown"),
            "project": os.getenv("RAILWAY_PROJECT_NAME", "unknown"),
        }
    }

# Include routers
from app.api import users, accounts, transactions, auth
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(accounts.router)
app.include_router(transactions.router)

# Error handler for database exceptions
from sqlalchemy.exc import SQLAlchemyError
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Database error: {str(exc)}")
    return JSONResponse(
        status_code=503,
        content={"detail": "Database service unavailable. Please try again later."}
    )

# Create a root user if none exists (for testing purposes)
@app.on_event("startup")
async def startup_event():
    """
    Create a default admin user if no users exist.
    This is for testing purposes only and should be removed in production.
    """
    try:
        logger.info("Starting application...")
        logger.info(f"Railway environment: {RAILWAY_ENVIRONMENT_NAME}")
        logger.info(f"Railway service: {RAILWAY_SERVICE_NAME}")
        logger.info(f"Railway public domain: {RAILWAY_PUBLIC_DOMAIN}")

        # Try to create the admin user, but don't fail if it doesn't work
        try:
            db = next(get_db())
            if db.query(User).count() == 0:
                from app.core.auth import get_password_hash
                admin_user = User(
                    username="admin",
                    email="admin@example.com",
                    password_hash=get_password_hash("admin"),
                    is_active=True
                )
                db.add(admin_user)
                db.commit()
                logger.info("Created default admin user")
        except Exception as e:
            logger.error(f"Could not create admin user: {str(e)}")
            logger.info("Will try to create admin user later when database is available")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")

from app.models.models import User
