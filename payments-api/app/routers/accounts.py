import random, string
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.finance import Account, AccountStatus
from app.schemas.schemas import AccountCreate, AccountOut

router = APIRouter()


def generate_account_no() -> str:
    """Generate a random 16-digit account number like a card PAN."""
    return "".join(random.choices(string.digits, k=16))


@router.post("/", response_model=AccountOut, status_code=201)
async def create_account(
    payload: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account_no = generate_account_no()
    account = Account(
        account_no = account_no,
        owner_id   = current_user.id,
        currency   = payload.currency.upper(),
        balance    = 0,
        status     = AccountStatus.ACTIVE,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.get("/", response_model=List[AccountOut])
async def list_my_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Account).where(Account.owner_id == current_user.id)
    )
    return result.scalars().all()


@router.get("/{account_no}", response_model=AccountOut)
async def get_account(
    account_no: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Account).where(
            Account.account_no == account_no,
            Account.owner_id   == current_user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account
