#!/usr/bin/env python
"""
Script to set up Supabase tables for the accounting backend.
This script creates the necessary tables in Supabase for the accounting application.
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
load_dotenv()

from app.core.supabase_client import supabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def create_tables():
    """Create the necessary tables in Supabase."""
    try:
        # Create users table
        logger.info("Creating users table...")
        supabase.table("users").execute_sql("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS ix_users_username_email ON users (username, email);
        """)
        
        # Create accounts table
        logger.info("Creating accounts table...")
        supabase.table("accounts").execute_sql("""
            CREATE TABLE IF NOT EXISTS accounts (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                account_type VARCHAR(50) NOT NULL,
                description TEXT,
                owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT check_valid_account_type CHECK (account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense'))
            );
            
            CREATE INDEX IF NOT EXISTS ix_accounts_owner_id_name ON accounts (owner_id, name);
            CREATE INDEX IF NOT EXISTS ix_accounts_account_type ON accounts (account_type);
        """)
        
        # Create transactions table
        logger.info("Creating transactions table...")
        supabase.table("transactions").execute_sql("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                reference_number VARCHAR(255) UNIQUE NOT NULL,
                description TEXT,
                transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_by_id INTEGER NOT NULL REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS ix_transactions_transaction_date ON transactions (transaction_date);
            CREATE INDEX IF NOT EXISTS ix_transactions_created_by_id ON transactions (created_by_id);
        """)
        
        # Create transaction_entries table
        logger.info("Creating transaction_entries table...")
        supabase.table("transaction_entries").execute_sql("""
            CREATE TABLE IF NOT EXISTS transaction_entries (
                id SERIAL PRIMARY KEY,
                debit_amount FLOAT NOT NULL DEFAULT 0.0,
                credit_amount FLOAT NOT NULL DEFAULT 0.0,
                description TEXT,
                transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
                account_id INTEGER NOT NULL REFERENCES accounts(id),
                CONSTRAINT check_debit_xor_credit CHECK 
                    ((debit_amount > 0 AND credit_amount = 0) OR (credit_amount > 0 AND debit_amount = 0))
            );
            
            CREATE INDEX IF NOT EXISTS ix_transaction_entries_transaction_id ON transaction_entries (transaction_id);
            CREATE INDEX IF NOT EXISTS ix_transaction_entries_account_id ON transaction_entries (account_id);
        """)
        
        logger.info("All tables created successfully!")
        return True
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        return False

def main():
    """Main function to set up Supabase tables."""
    if not supabase:
        logger.error("Supabase client not initialized. Check your environment variables.")
        return False
    
    logger.info("Setting up Supabase tables...")
    success = create_tables()
    
    if success:
        logger.info("Supabase setup completed successfully!")
    else:
        logger.error("Supabase setup failed.")
    
    return success

if __name__ == "__main__":
    main()
