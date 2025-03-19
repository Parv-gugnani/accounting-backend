"""
User repository module for Supabase database operations.
"""
import logging
from typing import Dict, List, Any, Optional
from app.schemas.schemas import UserCreate, UserUpdate, UserInDB
from app.repositories.supabase_repository import SupabaseRepository
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)

class UserRepository(SupabaseRepository[UserInDB]):
    """
    Repository for User operations using Supabase.
    """
    def __init__(self):
        super().__init__("users", UserInDB)
    
    async def create_user(self, user: UserCreate) -> UserInDB:
        """
        Create a new user with hashed password.
        """
        hashed_password = get_password_hash(user.password)
        user_data = {
            "username": user.username,
            "email": user.email,
            "password_hash": hashed_password,
            "is_active": True
        }
        return await self.create(user_data)
    
    async def get_by_username(self, username: str) -> Optional[UserInDB]:
        """
        Get a user by username.
        """
        try:
            response = self.table.select("*").eq("username", username).execute()
            if response.data and len(response.data) > 0:
                return UserInDB(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error getting user by username: {str(e)}")
            raise
    
    async def get_by_email(self, email: str) -> Optional[UserInDB]:
        """
        Get a user by email.
        """
        try:
            response = self.table.select("*").eq("email", email).execute()
            if response.data and len(response.data) > 0:
                return UserInDB(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            raise
    
    async def update_user(self, user_id: int, user_update: UserUpdate) -> Optional[UserInDB]:
        """
        Update a user.
        """
        update_data = user_update.dict(exclude_unset=True)
        
        # Hash the password if it's being updated
        if "password" in update_data:
            update_data["password_hash"] = get_password_hash(update_data.pop("password"))
        
        return await self.update(user_id, update_data)
