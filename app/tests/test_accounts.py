import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.models.models import User, Account
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

def test_create_account(test_db, token):
    # Test creating a new account
    response = client.post(
        "/accounts/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Cash",
            "account_type": "asset",
            "description": "Cash on hand"
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Cash"
    assert data["account_type"] == "asset"
    assert data["description"] == "Cash on hand"

def test_get_accounts(test_db, token):
    # Create a test account
    user = test_db.query(User).filter(User.username == "testuser").first()
    account = Account(name="Test Account", account_type="asset", owner_id=user.id)
    test_db.add(account)
    test_db.commit()
    
    # Test getting all accounts
    response = client.get(
        "/accounts/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Account"
    assert data[0]["account_type"] == "asset"

def test_get_account_by_id(test_db, token):
    # Create a test account
    user = test_db.query(User).filter(User.username == "testuser").first()
    account = Account(name="Test Account", account_type="asset", owner_id=user.id)
    test_db.add(account)
    test_db.commit()
    
    # Test getting an account by ID
    response = client.get(
        f"/accounts/{account.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Account"
    assert data["account_type"] == "asset"

def test_update_account(test_db, token):
    # Create a test account
    user = test_db.query(User).filter(User.username == "testuser").first()
    account = Account(name="Test Account", account_type="asset", owner_id=user.id)
    test_db.add(account)
    test_db.commit()
    
    # Test updating an account
    response = client.put(
        f"/accounts/{account.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Updated Account",
            "account_type": "liability",
            "description": "Updated description"
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Account"
    assert data["account_type"] == "liability"
    assert data["description"] == "Updated description"

def test_delete_account(test_db, token):
    # Create a test account
    user = test_db.query(User).filter(User.username == "testuser").first()
    account = Account(name="Test Account", account_type="asset", owner_id=user.id)
    test_db.add(account)
    test_db.commit()
    
    # Test deleting an account
    response = client.delete(
        f"/accounts/{account.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204
    
    # Verify the account is deleted
    response = client.get(
        f"/accounts/{account.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
