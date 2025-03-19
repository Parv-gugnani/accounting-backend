"""
Transaction repository module for Supabase database operations.
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.schemas.schemas import TransactionCreate, TransactionUpdate, TransactionInDB, TransactionEntryCreate
from app.repositories.supabase_repository import SupabaseRepository
from app.core.supabase_client import supabase

logger = logging.getLogger(__name__)

class TransactionRepository(SupabaseRepository[TransactionInDB]):
    """
    Repository for Transaction operations using Supabase.
    """
    def __init__(self):
        super().__init__("transactions", TransactionInDB)
    
    async def create_transaction_with_entries(
        self, 
        transaction: TransactionCreate, 
        entries: List[TransactionEntryCreate], 
        created_by_id: int
    ) -> Optional[TransactionInDB]:
        """
        Create a new transaction with its entries in a single operation.
        This implements a basic transaction (no pun intended) to ensure data consistency.
        """
        try:
            # Start a transaction-like operation (Supabase doesn't have true transactions)
            # First, create the transaction
            transaction_data = {
                "reference_number": transaction.reference_number,
                "description": transaction.description,
                "transaction_date": transaction.transaction_date.isoformat() if transaction.transaction_date else datetime.utcnow().isoformat(),
                "created_by_id": created_by_id
            }
            
            transaction_response = self.table.insert(transaction_data).execute()
            
            if not transaction_response.data or len(transaction_response.data) == 0:
                logger.error("Failed to create transaction")
                return None
            
            transaction_id = transaction_response.data[0]["id"]
            
            # Then create all entries
            entries_table = supabase.table("transaction_entries")
            for entry in entries:
                entry_data = {
                    "transaction_id": transaction_id,
                    "account_id": entry.account_id,
                    "debit_amount": entry.debit_amount,
                    "credit_amount": entry.credit_amount,
                    "description": entry.description
                }
                entries_table.insert(entry_data).execute()
            
            # Return the created transaction with its ID
            return TransactionInDB(**transaction_response.data[0])
        
        except Exception as e:
            logger.error(f"Error creating transaction with entries: {str(e)}")
            # In a real database with transactions, we would rollback here
            # Since Supabase doesn't support transactions, we'll need to manually clean up
            # This is a limitation of using Supabase without RLS policies
            raise
    
    async def get_transaction_with_entries(self, transaction_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a transaction with all its entries.
        """
        try:
            # Get the transaction
            transaction_response = self.table.select("*").eq("id", transaction_id).execute()
            
            if not transaction_response.data or len(transaction_response.data) == 0:
                return None
            
            transaction = transaction_response.data[0]
            
            # Get all entries for this transaction
            entries_table = supabase.table("transaction_entries")
            entries_response = entries_table.select("*").eq("transaction_id", transaction_id).execute()
            
            # Combine transaction with its entries
            result = {
                "transaction": transaction,
                "entries": entries_response.data if entries_response.data else []
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Error getting transaction with entries: {str(e)}")
            raise
    
    async def get_transactions_by_user(self, user_id: int) -> List[TransactionInDB]:
        """
        Get all transactions created by a specific user.
        """
        return await self.get_all({"created_by_id": user_id})
    
    async def get_transactions_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime, 
        user_id: Optional[int] = None
    ) -> List[TransactionInDB]:
        """
        Get all transactions within a date range, optionally filtered by user.
        """
        try:
            query = self.table.select("*")
            
            # Add date range filter
            query = query.gte("transaction_date", start_date.isoformat())
            query = query.lte("transaction_date", end_date.isoformat())
            
            # Add user filter if provided
            if user_id is not None:
                query = query.eq("created_by_id", user_id)
            
            response = query.execute()
            
            if response.data:
                return [TransactionInDB(**item) for item in response.data]
            return []
        
        except Exception as e:
            logger.error(f"Error getting transactions by date range: {str(e)}")
            raise
