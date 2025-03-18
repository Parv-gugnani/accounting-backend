from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import logging
from sqlalchemy.orm import Session
import os
import pathlib

from app.db.database import engine, Base, get_db
from app.api import users, accounts, transactions, auth
from app.models.models import User
from app.core.config import ALLOWED_ORIGINS, DEBUG

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

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Accounting System API",
    description="A backend for an accounting system with double-entry bookkeeping",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get base directory
BASE_DIR = pathlib.Path(__file__).parent

# Mount static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Set up templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(accounts.router)
app.include_router(transactions.router)

@app.get("/")
def read_root(request: Request):
    """
    Root endpoint that serves the frontend UI.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint to verify database connection.
    """
    try:
        # Check database connection
        db.execute("SELECT 1")
        
        # Check if static files directory exists
        static_dir = BASE_DIR / "static"
        static_exists = static_dir.exists()
        
        # Check if templates directory exists
        templates_dir = BASE_DIR / "templates"
        templates_exist = templates_dir.exists()
        
        # List files in directories if they exist
        static_files = list(static_dir.glob("**/*")) if static_exists else []
        template_files = list(templates_dir.glob("**/*")) if templates_exist else []
        
        return {
            "status": "healthy",
            "database": "connected",
            "static_directory": {
                "exists": static_exists,
                "path": str(static_dir),
                "files": [str(f.relative_to(static_dir)) for f in static_files if f.is_file()]
            },
            "templates_directory": {
                "exists": templates_exist,
                "path": str(templates_dir),
                "files": [str(f.relative_to(templates_dir)) for f in template_files if f.is_file()]
            },
            "environment": {
                "debug": DEBUG,
                "allowed_origins": ALLOWED_ORIGINS
            }
        }
    except Exception as e:
        logging.getLogger(__name__).error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# Create a root user if none exists (for testing purposes)
@app.on_event("startup")
async def startup_event():
    """
    Create a default admin user if no users exist.
    This is for testing purposes only and should be removed in production.
    """
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
