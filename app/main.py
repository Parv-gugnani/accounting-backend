from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import logging
from sqlalchemy.orm import Session

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

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="app/templates")

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
        # Try to execute a simple query
        db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

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
