from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.db.database import Base

class User(Base):
    """
    User model for system access and account ownership.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    accounts = relationship("Account", back_populates="owner", cascade="all, delete-orphan")
    
    # Indexes and constraints
    __table_args__ = (
        Index("ix_users_username_email", "username", "email"),
    )

class Account(Base):
    """
    Account model for financial accounts.
    Implements account types: asset, liability, equity, revenue, expense
    """
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    account_type = Column(String, nullable=False)  # asset, liability, equity, revenue, expense
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="accounts")
    transaction_entries = relationship("TransactionEntry", back_populates="account", cascade="all, delete-orphan")
    
    # Indexes and constraints
    __table_args__ = (
        CheckConstraint(
            "account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')", 
            name="check_valid_account_type"
        ),
        Index("ix_accounts_owner_id_name", "owner_id", "name"),
        Index("ix_accounts_account_type", "account_type"),
    )
    
    @property
    def balance(self):
        """
        Calculate account balance based on transaction entries.
        For asset and expense accounts: debit - credit
        For liability, equity, and revenue accounts: credit - debit
        """
        debit_sum = sum(entry.debit_amount for entry in self.transaction_entries)
        credit_sum = sum(entry.credit_amount for entry in self.transaction_entries)
        
        if self.account_type in ["asset", "expense"]:
            return debit_sum - credit_sum
        else:  # liability, equity, revenue
            return credit_sum - debit_sum

class Transaction(Base):
    """
    Transaction model to record financial transactions.
    Implements double-entry bookkeeping with transaction entries.
    """
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    reference_number = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    transaction_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    created_by = relationship("User")
    entries = relationship("TransactionEntry", back_populates="transaction", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("ix_transactions_transaction_date", "transaction_date"),
        Index("ix_transactions_created_by_id", "created_by_id"),
    )

class TransactionEntry(Base):
    """
    TransactionEntry model to record debits and credits for each account in a transaction.
    Implements the double-entry bookkeeping system.
    """
    __tablename__ = "transaction_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    debit_amount = Column(Float, default=0.0, nullable=False)
    credit_amount = Column(Float, default=0.0, nullable=False)
    description = Column(String, nullable=True)
    
    # Foreign keys
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    # Relationships
    transaction = relationship("Transaction", back_populates="entries")
    account = relationship("Account", back_populates="transaction_entries")
    
    # Indexes and constraints
    __table_args__ = (
        CheckConstraint(
            "(debit_amount > 0 AND credit_amount = 0) OR (credit_amount > 0 AND debit_amount = 0)",
            name="check_debit_xor_credit"
        ),
        Index("ix_transaction_entries_transaction_id", "transaction_id"),
        Index("ix_transaction_entries_account_id", "account_id"),
    )
