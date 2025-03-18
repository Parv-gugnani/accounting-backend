import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.models.models import User
from app.core.auth import get_password_hash

# Create an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="function")
def test_db():
    # Create the database tables
    Base.metadata.create_all(bind=engine)
    
    # Create a test user
    db = TestingSessionLocal()
    password_hash = get_password_hash("testpassword")
    test_user = User(username="testuser", email="test@example.com", password_hash=password_hash)
    db.add(test_user)
    db.commit()
    
    yield db  # Testing happens here
    
    # Clean up after the test
    db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def token(test_db):
    # Get a token for the test user
    response = client.post(
        "/auth/token",
        data={"username": "testuser", "password": "testpassword"},
    )
    return response.json()["access_token"]

def test_create_user(test_db):
    """Test creating a new user"""
    response = client.post(
        "/users/",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpassword"
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"
    assert "password" not in data  # Password should not be returned

def test_create_user_duplicate_username(test_db):
    """Test that creating a user with a duplicate username fails"""
    response = client.post(
        "/users/",
        json={
            "username": "testuser",  # This username already exists
            "email": "another@example.com",
            "password": "password123"
        },
    )
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]

def test_create_user_duplicate_email(test_db):
    """Test that creating a user with a duplicate email fails"""
    response = client.post(
        "/users/",
        json={
            "username": "uniqueuser",
            "email": "test@example.com",  # This email already exists
            "password": "password123"
        },
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]

def test_get_users(test_db, token):
    """Test retrieving all users"""
    response = client.get(
        "/users/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(u["username"] == "testuser" for u in data)

def test_get_current_user(test_db, token):
    """Test retrieving the current user's information"""
    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"

def test_get_user_by_id(test_db, token):
    """Test retrieving a user by ID"""
    # Get the user ID first
    user = test_db.query(User).filter(User.username == "testuser").first()
    
    response = client.get(
        f"/users/{user.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"

def test_get_nonexistent_user(test_db, token):
    """Test that retrieving a non-existent user returns a 404"""
    response = client.get(
        "/users/999",  # This ID should not exist
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]
