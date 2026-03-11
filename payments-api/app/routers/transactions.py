from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.finance import Transaction, Account
from app.schemas.schemas import TransferRequest, DepositRequest, TransactionOut
from app.services.transaction_service import process_transfer, process_deposit

router = APIRouter()


@router.post("/transfer", response_model=TransactionOut, status_code=201)
async def transfer(
    payload: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Transfer funds between two accounts.
    - Idempotent: re-submitting the same idempotency_key returns the original result.
    - Atomic: either both accounts update or neither does.
    """
    return await process_transfer(db, payload, current_user.id)


@router.post("/deposit", response_model=TransactionOut, status_code=201)
async def deposit(
    payload: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deposit funds into one of your accounts."""
    return await process_deposit(db, payload, current_user.id)


@router.get("/", response_model=List[TransactionOut])
async def list_my_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    """List all transactions where you are sender or receiver."""
    # Get current user's account IDs first
    accounts_result = await db.execute(
        select(Account.id).where(Account.owner_id == current_user.id)
    )
    account_ids = [row[0] for row in accounts_result.fetchall()]

    result = await db.execute(
        select(Transaction)
        .where(or_(
            Transaction.sender_id.in_(account_ids),
            Transaction.receiver_id.in_(account_ids),
        ))
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()
