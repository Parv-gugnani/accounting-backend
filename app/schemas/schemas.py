from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Account schemas
class AccountBase(BaseModel):
    name: str
    account_type: str
    description: Optional[str] = None
    
    @validator('account_type')
    def validate_account_type(cls, v):
        valid_types = ['asset', 'liability', 'equity', 'revenue', 'expense']
        if v not in valid_types:
            raise ValueError(f'account_type must be one of {valid_types}')
        return v

class AccountCreate(AccountBase):
    pass

class AccountResponse(AccountBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    balance: float = 0.0
    
    class Config:
        from_attributes = True

# Transaction Entry schemas
class TransactionEntryBase(BaseModel):
    account_id: int
    debit_amount: float = 0.0
    credit_amount: float = 0.0
    description: Optional[str] = None
    
    @validator('debit_amount', 'credit_amount')
    def validate_amounts(cls, v):
        if v < 0:
            raise ValueError('Amount cannot be negative')
        return v

class TransactionEntryCreate(TransactionEntryBase):
    pass

class TransactionEntryResponse(TransactionEntryBase):
    id: int
    transaction_id: int
    
    class Config:
        from_attributes = True

# Transaction schemas
class TransactionBase(BaseModel):
    reference_number: str
    description: Optional[str] = None
    transaction_date: Optional[datetime] = None

class TransactionCreate(TransactionBase):
    entries: List[TransactionEntryCreate]
    
    @validator('entries')
    def validate_double_entry(cls, entries):
        if not entries or len(entries) < 2:
            raise ValueError('A transaction must have at least two entries')
        
        total_debit = sum(entry.debit_amount for entry in entries)
        total_credit = sum(entry.credit_amount for entry in entries)
        
        if round(total_debit, 2) != round(total_credit, 2):
            raise ValueError('Total debits must equal total credits')
        
        return entries

class TransactionResponse(TransactionBase):
    id: int
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    entries: List[TransactionEntryResponse]
    
    class Config:
        from_attributes = True

# Balance schema
class AccountBalance(BaseModel):
    account_id: int
    account_name: str
    account_type: str
    balance: float
