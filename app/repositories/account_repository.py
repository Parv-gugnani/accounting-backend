"""
Account repository module for Supabase database operations.
"""
import logging
from typing import Dict, List, Any, Optional
from app.schemas.schemas import AccountCreate, AccountUpdate, AccountInDB
from app.repositories.supabase_repository import SupabaseRepository

logger = logging.getLogger(__name__)

class AccountRepository(SupabaseRepository[AccountInDB]):
    """
    Repository for Account operations using Supabase.
    """
    def __init__(self):
        super().__init__("accounts", AccountInDB)
    
    async def create_account(self, account: AccountCreate, owner_id: int) -> AccountInDB:
        """
        Create a new account.
        """
        account_data = {
            "name": account.name,
            "account_type": account.account_type,
            "description": account.description,
            "owner_id": owner_id
        }
        return await self.create(account_data)
    
    async def get_accounts_by_owner(self, owner_id: int) -> List[AccountInDB]:
        """
        Get all accounts for a specific owner.
        """
        return await self.get_all({"owner_id": owner_id})
    
    async def get_accounts_by_type(self, account_type: str, owner_id: Optional[int] = None) -> List[AccountInDB]:
        """
        Get all accounts of a specific type, optionally filtered by owner.
        """
        filters = {"account_type": account_type}
        if owner_id is not None:
            filters["owner_id"] = owner_id
        
        return await self.get_all(filters)
    
    async def update_account(self, account_id: int, account_update: AccountUpdate) -> Optional[AccountInDB]:
        """
        Update an account.
        """
        update_data = account_update.dict(exclude_unset=True)
        return await self.update(account_id, update_data)
    
    async def calculate_balance(self, account_id: int) -> float:
        """
        Calculate the balance of an account based on its transaction entries.
        """
        try:
            # First get the account to determine its type
            account_response = self.table.select("*").eq("id", account_id).execute()
            if not account_response.data or len(account_response.data) == 0:
                return 0.0
            
            account = AccountInDB(**account_response.data[0])
            
            # Get all transaction entries for this account
            transaction_entries_table = self.supabase.table("transaction_entries")
            entries_response = transaction_entries_table.select("*").eq("account_id", account_id).execute()
            
            if not entries_response.data:
                return 0.0
            
            # Calculate balance based on account type
            debit_sum = sum(entry.get("debit_amount", 0) for entry in entries_response.data)
            credit_sum = sum(entry.get("credit_amount", 0) for entry in entries_response.data)
            
            if account.account_type in ["asset", "expense"]:
                return debit_sum - credit_sum
            else:  # liability, equity, revenue
                return credit_sum - debit_sum
                
        except Exception as e:
            logger.error(f"Error calculating account balance: {str(e)}")
            return 0.0
