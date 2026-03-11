from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.finance import LedgerEntry, Account
from app.schemas.schemas import LedgerEntryOut

router = APIRouter()


@router.get("/{account_no}", response_model=List[LedgerEntryOut])
async def get_ledger(
    account_no: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
):
    """
    Retrieve the immutable ledger (full audit trail) for a given account.
    Every debit and credit is recorded here permanently — nothing is ever deleted.
    This is the source of truth for account history.
    """
    # Ownership check
    acc_result = await db.execute(
        select(Account).where(
            Account.account_no == account_no,
            Account.owner_id   == current_user.id,
        )
    )
    account = acc_result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    entries_result = await db.execute(
        select(LedgerEntry)
        .where(LedgerEntry.account_id == account.id)
        .order_by(LedgerEntry.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return entries_result.scalars().all()
