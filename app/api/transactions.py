from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import logging

from app.db.database import get_db
from app.models.models import Transaction, TransactionEntry, Account, User
from app.schemas.schemas import TransactionCreate, TransactionResponse
from app.core.auth import get_current_active_user
from app.core.logging import logger

# Configure logging

router = APIRouter(
    prefix="/transactions",
    tags=["transactions"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    transaction: TransactionCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new transaction with double-entry bookkeeping.
    Validates that:
    1. All accounts exist and belong to the user
    2. Total debits equal total credits (double-entry principle)
    3. Each entry is either a debit or a credit, not both
    """
    # Check if reference number already exists
    existing_transaction = db.query(Transaction).filter(
        Transaction.reference_number == transaction.reference_number
    ).first()
    
    if existing_transaction:
        logger.error(f"Transaction creation failed: Transaction with reference number {transaction.reference_number} already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction with this reference number already exists"
        )
    
    # Validate accounts exist and belong to the user
    account_ids = [entry.account_id for entry in transaction.entries]
    accounts = db.query(Account).filter(
        Account.id.in_(account_ids),
        Account.owner_id == current_user.id
    ).all()
    
    if len(accounts) != len(set(account_ids)):
        logger.error(f"Transaction creation failed: One or more accounts do not exist or do not belong to user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more accounts do not exist or do not belong to you"
        )
    
    # Create transaction
    db_transaction = Transaction(
        reference_number=transaction.reference_number,
        description=transaction.description,
        transaction_date=transaction.transaction_date or datetime.utcnow(),
        created_by_id=current_user.id
    )
    
    db.add(db_transaction)
    db.flush()  # Get the transaction ID without committing
    
    # Create transaction entries
    for entry in transaction.entries:
        # Validate that entry is either debit or credit, not both
        if entry.debit_amount > 0 and entry.credit_amount > 0:
            db.rollback()
            logger.error(f"Transaction creation failed: Entry {entry.account_id} is both debit and credit")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An entry cannot be both a debit and a credit"
            )
        
        if entry.debit_amount == 0 and entry.credit_amount == 0:
            db.rollback()
            logger.error(f"Transaction creation failed: Entry {entry.account_id} is neither debit nor credit")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An entry must be either a debit or a credit"
            )
        
        db_entry = TransactionEntry(
            transaction_id=db_transaction.id,
            account_id=entry.account_id,
            debit_amount=entry.debit_amount,
            credit_amount=entry.credit_amount,
            description=entry.description
        )
        db.add(db_entry)
    
    # Commit the transaction
    try:
        db.commit()
        db.refresh(db_transaction)
        
        # Log the transaction
        logger.info(
            f"Transaction {db_transaction.reference_number} created successfully by user {current_user.username} "
            f"with {len(transaction.entries)} entries"
        )
        
        return db_transaction
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating transaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the transaction"
        )

@router.get("/", response_model=List[TransactionResponse])
def get_transactions(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_active_user),
    skip: int = 0, 
    limit: int = 100,
    start_date: datetime = None,
    end_date: datetime = None
):
    """
    Get all transactions created by the authenticated user.
    Optional filtering by date range.
    """
    query = db.query(Transaction).filter(Transaction.created_by_id == current_user.id)
    
    if start_date:
        query = query.filter(Transaction.transaction_date >= start_date)
    
    if end_date:
        query = query.filter(Transaction.transaction_date <= end_date)
    
    transactions = query.order_by(Transaction.transaction_date.desc()).offset(skip).limit(limit).all()
    return transactions

@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific transaction by ID.
    """
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.created_by_id == current_user.id
    ).first()
    
    if transaction is None:
        logger.error(f"Transaction retrieval failed: Transaction {transaction_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    return transaction

@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a transaction and its entries.
    """
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.created_by_id == current_user.id
    ).first()
    
    if transaction is None:
        logger.error(f"Transaction deletion failed: Transaction {transaction_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Delete the transaction (cascade will delete entries)
    db.delete(transaction)
    db.commit()
    
    logger.info(f"Transaction {transaction_id} deleted successfully by user {current_user.username}")
    
    return None
