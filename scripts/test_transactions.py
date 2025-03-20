#!/usr/bin/env python
"""
Script to test the transactions functionality with Supabase integration.
"""
import os
import sys
import json
import logging
import requests
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# API URL
BASE_URL = "http://127.0.0.1:8000"

def get_token(username, password):
    """Get an authentication token."""
    token_url = f"{BASE_URL}/auth/token"
    data = {
        "username": username,
        "password": password
    }
    
    logger.info(f"Attempting to authenticate with username: {username}")
    response = requests.post(token_url, data=data)
    
    if response.status_code == 200:
        token_data = response.json()
        logger.info(f"Authentication successful for user: {username}")
        return token_data["access_token"]
    else:
        logger.error(f"Authentication failed: {response.text}")
        return None

def create_user(username, email, password):
    """Create a new user."""
    users_url = f"{BASE_URL}/users/"
    data = {
        "username": username,
        "email": email,
        "password": password
    }
    
    logger.info(f"Attempting to create user: {username}")
    response = requests.post(users_url, json=data)
    
    if response.status_code == 200 or response.status_code == 201:
        logger.info(f"User created: {username}")
        return response.json()
    else:
        logger.error(f"Failed to create user: {response.text}")
        return None

def create_account(token, name, account_type, description=None):
    """Create a new account."""
    accounts_url = f"{BASE_URL}/accounts/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "name": name,
        "account_type": account_type,
        "description": description
    }
    
    logger.info(f"Attempting to create account: {name}")
    response = requests.post(accounts_url, headers=headers, json=data)
    
    if response.status_code == 200 or response.status_code == 201:
        logger.info(f"Account created: {name}")
        return response.json()
    else:
        logger.error(f"Failed to create account: {response.text}")
        return None

def get_accounts(token):
    """Get all accounts for the current user."""
    accounts_url = f"{BASE_URL}/accounts/"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    logger.info("Retrieving accounts")
    response = requests.get(accounts_url, headers=headers)
    
    if response.status_code == 200:
        accounts = response.json()
        logger.info(f"Retrieved {len(accounts)} accounts")
        return accounts
    else:
        logger.error(f"Failed to get accounts: {response.text}")
        return []

def create_transaction(token, reference_number, description, entries):
    """Create a new transaction with entries."""
    transactions_url = f"{BASE_URL}/transactions/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "reference_number": reference_number,
        "description": description,
        "transaction_date": datetime.utcnow().isoformat(),
        "entries": entries
    }
    
    logger.info(f"Attempting to create transaction: {reference_number}")
    response = requests.post(transactions_url, headers=headers, json=data)
    
    if response.status_code == 200 or response.status_code == 201:
        logger.info(f"Transaction created: {reference_number}")
        return response.json()
    else:
        logger.error(f"Failed to create transaction: {response.text}")
        return None

def get_account_balance(token, account_id):
    """Get the balance of an account."""
    balance_url = f"{BASE_URL}/accounts/{account_id}/balance"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    logger.info(f"Retrieving balance for account: {account_id}")
    response = requests.get(balance_url, headers=headers)
    
    if response.status_code == 200:
        balance_data = response.json()
        logger.info(f"Account {account_id} balance: {balance_data['balance']}")
        return balance_data
    else:
        logger.error(f"Failed to get account balance: {response.text}")
        return None

def main():
    """Main function to test transactions functionality."""
    # Generate a unique username to avoid conflicts
    unique_id = str(uuid.uuid4())[:8]
    username = f"testuser_{unique_id}"
    email = f"testuser_{unique_id}@example.com"
    password = "testpassword123"
    
    logger.info(f"Testing with unique user: {username}")
    
    # Create a test user
    user = create_user(username, email, password)
    if not user:
        logger.error("Failed to create test user. Cannot proceed with tests.")
        return
    
    # Get authentication token
    token = get_token(username, password)
    
    if not token:
        logger.error("Authentication failed. Cannot proceed with tests.")
        return
    
    logger.info("Authentication successful!")
    
    # Create accounts
    cash_account = create_account(token, "Cash", "asset", "Cash on hand")
    if not cash_account:
        logger.error("Failed to create Cash account. Cannot proceed with tests.")
        return
    
    expense_account = create_account(token, "Office Supplies", "expense", "Office supplies expenses")
    if not expense_account:
        logger.error("Failed to create Office Supplies account. Cannot proceed with tests.")
        return
    
    # Create a test transaction
    entries = [
        {
            "account_id": cash_account["id"],
            "credit_amount": 100.0,
            "debit_amount": 0.0,
            "description": "Cash payment"
        },
        {
            "account_id": expense_account["id"],
            "credit_amount": 0.0,
            "debit_amount": 100.0,
            "description": "Office supplies expense"
        }
    ]
    
    transaction = create_transaction(
        token,
        f"TX-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "Purchase of office supplies",
        entries
    )
    
    if not transaction:
        logger.error("Failed to create test transaction.")
        return
    
    # Check account balances
    cash_balance = get_account_balance(token, cash_account["id"])
    expense_balance = get_account_balance(token, expense_account["id"])
    
    logger.info("Test completed successfully!")
    logger.info(f"Cash account balance: {cash_balance['balance'] if cash_balance else 'Unknown'}")
    logger.info(f"Expense account balance: {expense_balance['balance'] if expense_balance else 'Unknown'}")

if __name__ == "__main__":
    main()
