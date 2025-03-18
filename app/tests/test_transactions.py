import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import date, datetime

from app.db.database import Base, get_db
from app.main import app
from app.models.models import User, Account, Transaction, TransactionEntry
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

@pytest.fixture(scope="function")
def test_accounts(test_db, token):
    # Create test accounts for transactions
    user = test_db.query(User).filter(User.username == "testuser").first()
    
    # Create Cash account (Asset)
    cash_account = Account(
        name="Cash", 
        account_type="asset", 
        description="Cash on hand",
        owner_id=user.id
    )
    
    # Create Revenue account
    revenue_account = Account(
        name="Revenue", 
        account_type="revenue", 
        description="Sales revenue",
        owner_id=user.id
    )
    
    # Create Expense account
    expense_account = Account(
        name="Expenses", 
        account_type="expense", 
        description="General expenses",
        owner_id=user.id
    )
    
    test_db.add_all([cash_account, revenue_account, expense_account])
    test_db.commit()
    
    # Refresh to get the IDs
    test_db.refresh(cash_account)
    test_db.refresh(revenue_account)
    test_db.refresh(expense_account)
    
    # Create an initial transaction to set up the cash account with a balance
    initial_transaction = Transaction(
        reference_number="INIT-001",
        description="Initial balance",
        transaction_date=datetime.now(),
        created_by_id=user.id
    )
    test_db.add(initial_transaction)
    test_db.flush()  # Get ID without committing
    
    # Add a transaction entry to set up initial cash balance
    initial_entry = TransactionEntry(
        transaction_id=initial_transaction.id,
        account_id=cash_account.id,
        debit_amount=1000.0,
        credit_amount=0.0
    )
    
    # Add a corresponding equity entry for double-entry bookkeeping
    equity_account = Account(
        name="Equity", 
        account_type="equity", 
        description="Owner's equity",
        owner_id=user.id
    )
    test_db.add(equity_account)
    test_db.flush()
    
    equity_entry = TransactionEntry(
        transaction_id=initial_transaction.id,
        account_id=equity_account.id,
        debit_amount=0.0,
        credit_amount=1000.0
    )
    
    test_db.add_all([initial_entry, equity_entry])
    test_db.commit()
    
    # Refresh accounts to update relationships
    test_db.refresh(cash_account)
    test_db.refresh(revenue_account)
    test_db.refresh(expense_account)
    test_db.refresh(equity_account)
    
    return {
        "cash": cash_account,
        "revenue": revenue_account,
        "expense": expense_account,
        "equity": equity_account
    }

def test_create_transaction(test_db, token, test_accounts):
    """Test creating a valid transaction with double-entry bookkeeping"""
    # Create a transaction (Revenue recognition)
    response = client.post(
        "/transactions/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "reference_number": "INV-001",
            "description": "Sales revenue",
            "date": str(date.today()),
            "entries": [
                {
                    "account_id": test_accounts["cash"].id,
                    "entry_type": "debit",
                    "amount": 500.00
                },
                {
                    "account_id": test_accounts["revenue"].id,
                    "entry_type": "credit",
                    "amount": 500.00
                }
            ]
        },
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["reference_number"] == "INV-001"
    assert data["description"] == "Sales revenue"
    assert len(data["entries"]) == 2
    
    # Check that account balances were updated correctly
    cash_account = test_db.query(Account).filter(Account.id == test_accounts["cash"].id).first()
    revenue_account = test_db.query(Account).filter(Account.id == test_accounts["revenue"].id).first()
    
    assert cash_account.balance == 1500.00  # 1000 + 500
    assert revenue_account.balance == 500.00  # 0 + 500

def test_create_transaction_invalid_double_entry(test_db, token, test_accounts):
    """Test that transaction creation fails when debits don't equal credits"""
    response = client.post(
        "/transactions/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "reference_number": "INV-002",
            "description": "Invalid transaction",
            "date": str(date.today()),
            "entries": [
                {
                    "account_id": test_accounts["cash"].id,
                    "entry_type": "debit",
                    "amount": 300.00
                },
                {
                    "account_id": test_accounts["revenue"].id,
                    "entry_type": "credit",
                    "amount": 500.00
                }
            ]
        },
    )
    
    assert response.status_code == 400
    assert "Total debits must equal total credits" in response.json()["detail"]
    
    # Check that account balances were not updated
    cash_account = test_db.query(Account).filter(Account.id == test_accounts["cash"].id).first()
    revenue_account = test_db.query(Account).filter(Account.id == test_accounts["revenue"].id).first()
    
    assert cash_account.balance == 1000.00  # Unchanged
    assert revenue_account.balance == 0.00  # Unchanged

def test_get_transactions(test_db, token, test_accounts):
    """Test retrieving all transactions"""
    # Create a test transaction
    user = test_db.query(User).filter(User.username == "testuser").first()
    
    # Create a transaction first
    response = client.post(
        "/transactions/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "reference_number": "INV-003",
            "description": "Test transaction",
            "date": str(date.today()),
            "entries": [
                {
                    "account_id": test_accounts["cash"].id,
                    "entry_type": "debit",
                    "amount": 200.00
                },
                {
                    "account_id": test_accounts["revenue"].id,
                    "entry_type": "credit",
                    "amount": 200.00
                }
            ]
        },
    )
    
    # Test getting all transactions
    response = client.get(
        "/transactions/",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(t["reference_number"] == "INV-003" for t in data)

def test_delete_transaction(test_db, token, test_accounts):
    """Test deleting a transaction and verifying that account balances are restored"""
    # Create a transaction to delete
    response = client.post(
        "/transactions/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "reference_number": "INV-004",
            "description": "Transaction to delete",
            "date": str(date.today()),
            "entries": [
                {
                    "account_id": test_accounts["cash"].id,
                    "entry_type": "credit",
                    "amount": 300.00
                },
                {
                    "account_id": test_accounts["expense"].id,
                    "entry_type": "debit",
                    "amount": 300.00
                }
            ]
        },
    )
    
    transaction_id = response.json()["id"]
    
    # Check balances after transaction
    cash_account = test_db.query(Account).filter(Account.id == test_accounts["cash"].id).first()
    expense_account = test_db.query(Account).filter(Account.id == test_accounts["expense"].id).first()
    
    assert cash_account.balance == 700.00  # 1000 - 300
    assert expense_account.balance == 300.00  # 0 + 300
    
    # Delete the transaction
    response = client.delete(
        f"/transactions/{transaction_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 204
    
    # Check that account balances were restored
    cash_account = test_db.query(Account).filter(Account.id == test_accounts["cash"].id).first()
    expense_account = test_db.query(Account).filter(Account.id == test_accounts["expense"].id).first()
    
    assert cash_account.balance == 1000.00  # Restored to original
    assert expense_account.balance == 0.00  # Restored to original
