"""
Supabase repository module for database operations.
This provides an abstraction layer over Supabase for CRUD operations.
"""
import logging
from typing import Dict, List, Any, Optional, Type, TypeVar, Generic
from pydantic import BaseModel

from app.db.database import get_table, supabase_transaction

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class SupabaseRepository(Generic[T]):
    """
    Generic repository for Supabase operations.
    """
    def __init__(self, table_name: str, model_class: Type[T]):
        self.table_name = table_name
        self.model_class = model_class
        self.table = get_table(table_name)

    async def create(self, data: Dict[str, Any]) -> T:
        """
        Create a new record in the table.
        """
        try:
            response = self.table.insert(data).execute()
            if response.data and len(response.data) > 0:
                return self.model_class(**response.data[0])
            raise ValueError("Failed to create record")
        except Exception as e:
            logger.error(f"Error creating record in {self.table_name}: {str(e)}")
            raise

    async def get_by_id(self, id: int) -> Optional[T]:
        """
        Get a record by ID.
        """
        try:
            response = self.table.select("*").eq("id", id).execute()
            if response.data and len(response.data) > 0:
                return self.model_class(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error getting record by ID from {self.table_name}: {str(e)}")
            raise

    async def get_all(self, filters: Optional[Dict[str, Any]] = None) -> List[T]:
        """
        Get all records, optionally filtered.
        """
        try:
            query = self.table.select("*")
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            response = query.execute()
            
            if response.data:
                return [self.model_class(**item) for item in response.data]
            return []
        except Exception as e:
            logger.error(f"Error getting records from {self.table_name}: {str(e)}")
            raise

    async def update(self, id: int, data: Dict[str, Any]) -> Optional[T]:
        """
        Update a record by ID.
        """
        try:
            response = self.table.update(data).eq("id", id).execute()
            if response.data and len(response.data) > 0:
                return self.model_class(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error updating record in {self.table_name}: {str(e)}")
            raise

    async def delete(self, id: int) -> bool:
        """
        Delete a record by ID.
        """
        try:
            response = self.table.delete().eq("id", id).execute()
            return response.data is not None and len(response.data) > 0
        except Exception as e:
            logger.error(f"Error deleting record from {self.table_name}: {str(e)}")
            raise

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records, optionally filtered.
        """
        try:
            query = self.table.select("count", count="exact")
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            response = query.execute()
            
            if response.count is not None:
                return response.count
            return 0
        except Exception as e:
            logger.error(f"Error counting records in {self.table_name}: {str(e)}")
            raise
