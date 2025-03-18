from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models.models import Account, User
from app.schemas.schemas import AccountCreate, AccountResponse, AccountBalance
from app.core.auth import get_current_active_user

router = APIRouter(
    prefix="/accounts",
    tags=["accounts"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    account: AccountCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new account for the authenticated user.
    """
    # Check if account with same name already exists for this user
    existing_account = db.query(Account).filter(
        Account.owner_id == current_user.id,
        Account.name == account.name
    ).first()
    
    if existing_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account with this name already exists"
        )
    
    # Create new account
    db_account = Account(
        name=account.name,
        account_type=account.account_type,
        description=account.description,
        owner_id=current_user.id
    )
    
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    
    return db_account

@router.get("/", response_model=List[AccountResponse])
def get_accounts(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_active_user),
    skip: int = 0, 
    limit: int = 100,
    account_type: str = None
):
    """
    Get all accounts for the authenticated user.
    Optional filtering by account type.
    """
    query = db.query(Account).filter(Account.owner_id == current_user.id)
    
    if account_type:
        valid_types = ['asset', 'liability', 'equity', 'revenue', 'expense']
        if account_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid account type. Must be one of {valid_types}"
            )
        query = query.filter(Account.account_type == account_type)
    
    accounts = query.offset(skip).limit(limit).all()
    return accounts

@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific account by ID.
    """
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.owner_id == current_user.id
    ).first()
    
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    return account

@router.get("/{account_id}/balance", response_model=AccountBalance)
def get_account_balance(
    account_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the balance of a specific account.
    """
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.owner_id == current_user.id
    ).first()
    
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    return {
        "account_id": account.id,
        "account_name": account.name,
        "account_type": account.account_type,
        "balance": account.balance
    }

@router.put("/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: int,
    account_update: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an existing account.
    """
    db_account = db.query(Account).filter(
        Account.id == account_id,
        Account.owner_id == current_user.id
    ).first()
    
    if db_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Check if another account with the same name exists
    existing_account = db.query(Account).filter(
        Account.owner_id == current_user.id,
        Account.name == account_update.name,
        Account.id != account_id
    ).first()
    
    if existing_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Another account with this name already exists"
        )
    
    # Update account
    db_account.name = account_update.name
    db_account.account_type = account_update.account_type
    db_account.description = account_update.description
    
    db.commit()
    db.refresh(db_account)
    
    return db_account

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete an account.
    """
    db_account = db.query(Account).filter(
        Account.id == account_id,
        Account.owner_id == current_user.id
    ).first()
    
    if db_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Check if the account has transactions
    if db_account.transaction_entries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete account with existing transactions"
        )
    
    db.delete(db_account)
    db.commit()
    
    return None
