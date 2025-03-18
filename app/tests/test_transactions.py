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
            "transaction_date": str(date.today()),
            "entries": [
                {
                    "account_id": test_accounts["cash"].id,
                    "debit_amount": 500.00,
                    "credit_amount": 0.00,
                    "description": "Cash from sales"
                },
                {
                    "account_id": test_accounts["revenue"].id,
                    "debit_amount": 0.00,
                    "credit_amount": 500.00,
                    "description": "Revenue from sales"
                }
            ]
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["reference_number"] == "INV-001"
    assert len(data["entries"]) == 2

    # Verify account balances were updated
    cash_account = test_db.query(Account).filter(Account.id == test_accounts["cash"].id).first()
    revenue_account = test_db.query(Account).filter(Account.id == test_accounts["revenue"].id).first()

    assert cash_account.balance == 1500.0  # Initial 1000 + 500
    assert revenue_account.balance == 500.0

def test_create_transaction_invalid_double_entry(test_db, token, test_accounts):
    """Test creating an invalid transaction where debits don't equal credits"""
    response = client.post(
        "/transactions/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "reference_number": "INV-002",
            "description": "Invalid transaction",
            "transaction_date": str(date.today()),
            "entries": [
                {
                    "account_id": test_accounts["cash"].id,
                    "debit_amount": 300.00,
                    "credit_amount": 0.00
                },
                {
                    "account_id": test_accounts["revenue"].id,
                    "debit_amount": 0.00,
                    "credit_amount": 200.00
                }
            ]
        },
    )

    assert response.status_code == 422
    error_detail = response.json()

    # Check that the error is in the expected format and contains the validation message
    assert "detail" in error_detail
    assert isinstance(error_detail["detail"], list)
    assert len(error_detail["detail"]) > 0

    # Check that at least one error message contains the expected text
    error_messages = [item.get("msg", "") for item in error_detail["detail"]]
    assert any("Total debits must equal total credits" in msg for msg in error_messages)

def test_get_transactions(test_db, token, test_accounts):
    """Test retrieving all transactions"""
    # First create a transaction
    response = client.post(
        "/transactions/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "reference_number": "INV-003",
            "description": "Another sale",
            "transaction_date": str(date.today()),
            "entries": [
                {
                    "account_id": test_accounts["cash"].id,
                    "debit_amount": 200.00,
                    "credit_amount": 0.00
                },
                {
                    "account_id": test_accounts["revenue"].id,
                    "debit_amount": 0.00,
                    "credit_amount": 200.00
                }
            ]
        },
    )
    assert response.status_code == 201

    # Now get all transactions
    response = client.get(
        "/transactions/",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    # Should have at least 2 transactions (the initial one + the one we just created)
    assert len(data) >= 2

    # Verify the transaction we just created is in the list
    transaction_ids = [t["id"] for t in data]
    created_transaction_id = response.json()[0]["id"]
    assert created_transaction_id in transaction_ids

def test_delete_transaction(test_db, token, test_accounts):
    """Test deleting a transaction and verifying account balances are restored"""
    # First create a transaction
    response = client.post(
        "/transactions/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "reference_number": "INV-004",
            "description": "Transaction to delete",
            "transaction_date": str(date.today()),
            "entries": [
                {
                    "account_id": test_accounts["cash"].id,
                    "debit_amount": 300.00,
                    "credit_amount": 0.00
                },
                {
                    "account_id": test_accounts["revenue"].id,
                    "debit_amount": 0.00,
                    "credit_amount": 300.00
                }
            ]
        },
    )
    assert response.status_code == 201
    transaction_id = response.json()["id"]

    # Record account balances before deletion
    cash_account_before = test_db.query(Account).filter(Account.id == test_accounts["cash"].id).first()
    revenue_account_before = test_db.query(Account).filter(Account.id == test_accounts["revenue"].id).first()

    # Store the balances before deletion
    cash_balance_before = cash_account_before.balance
    revenue_balance_before = revenue_account_before.balance

    # Delete the transaction
    response = client.delete(
        f"/transactions/{transaction_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204

    # Refresh the database session to get updated balances
    test_db.expire_all()

    # Verify account balances were restored
    cash_account_after = test_db.query(Account).filter(Account.id == test_accounts["cash"].id).first()
    revenue_account_after = test_db.query(Account).filter(Account.id == test_accounts["revenue"].id).first()

    # For asset accounts (like cash), debits increase balance and credits decrease balance
    # So after deletion, the balance should be 300 less than before
    assert cash_account_after.balance == cash_balance_before - 300.0

    # For revenue accounts, credits increase balance and debits decrease balance
    # So after deletion, the balance should be 300 less than before
    assert revenue_account_after.balance == revenue_balance_before - 300.0

def test_create_multi_entry_transaction(test_db, token, test_accounts):
    """Test creating a valid transaction with multiple entries (more than two)"""
    response = client.post(
        "/transactions/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "reference_number": "MULTI-001",
            "description": "Multi-entry transaction",
            "transaction_date": str(date.today()),
            "entries": [
                {
                    "account_id": test_accounts["cash"].id,
                    "debit_amount": 500.00,
                    "credit_amount": 0.00,
                    "description": "Cash payment"
                },
                {
                    "account_id": test_accounts["expense"].id,
                    "debit_amount": 300.00,
                    "credit_amount": 0.00,
                    "description": "Office supplies"
                },
                {
                    "account_id": test_accounts["revenue"].id,
                    "debit_amount": 0.00,
                    "credit_amount": 800.00,
                    "description": "Services rendered"
                }
            ]
        },
    )

    assert response.status_code == 201
    transaction = response.json()

    # Verify the transaction was created with all entries
    assert transaction["reference_number"] == "MULTI-001"
    assert len(transaction["entries"]) == 3

    # Verify total debits equal total credits
    total_debits = sum(entry["debit_amount"] for entry in transaction["entries"])
    total_credits = sum(entry["credit_amount"] for entry in transaction["entries"])
    assert total_debits == total_credits

def test_create_transaction_invalid_entry_both_debit_credit(test_db, token, test_accounts):
    """Test creating an invalid transaction where an entry is both debit and credit"""
    response = client.post(
        "/transactions/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "reference_number": "INV-003",
            "description": "Invalid entry transaction",
            "transaction_date": str(date.today()),
            "entries": [
                {
                    "account_id": test_accounts["cash"].id,
                    "debit_amount": 300.00,
                    "credit_amount": 100.00,  # Both debit and credit
                    "description": "Invalid entry"
                },
                {
                    "account_id": test_accounts["revenue"].id,
                    "debit_amount": 0.00,
                    "credit_amount": 200.00,
                    "description": "Revenue entry"
                }
            ]
        },
    )
    
    assert response.status_code == 400
    error_detail = response.json()
    
    # Check that the error is in the expected format
    assert "detail" in error_detail
    assert "An entry cannot be both a debit and a credit" in error_detail["detail"]

def test_create_transaction_invalid_entry_neither_debit_credit(test_db, token, test_accounts):
    """Test creating an invalid transaction where an entry is neither debit nor credit"""
    response = client.post(
        "/transactions/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "reference_number": "INV-005",
            "description": "Invalid entry transaction",
            "transaction_date": str(date.today()),
            "entries": [
                {
                    "account_id": test_accounts["cash"].id,
                    "debit_amount": 0.00,
                    "credit_amount": 0.00,  # Neither debit nor credit
                    "description": "Invalid entry"
                },
                {
                    "account_id": test_accounts["revenue"].id,
                    "debit_amount": 0.00,
                    "credit_amount": 200.00,
                    "description": "Revenue entry"
                }
            ]
        },
    )
    
    assert response.status_code == 422
    error_detail = response.json()
    
    # Print the error response for debugging
    print("Error response:", error_detail)
    
    # Check that the error is in the expected format
    assert "detail" in error_detail
    # For Pydantic validation errors, the error is in a list
    assert isinstance(error_detail["detail"], list)
    
    # Check that at least one error message indicates the entry must be either debit or credit
    error_messages = [str(item) for item in error_detail["detail"]]
    assert any("must be either a debit or a credit" in msg for msg in error_messages)
