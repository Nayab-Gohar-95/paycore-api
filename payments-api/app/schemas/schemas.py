from pydantic import BaseModel, EmailStr, Field, field_validator
from decimal import Decimal
from datetime import datetime
from typing import Optional
from app.models.finance import AccountStatus, TransactionStatus, TransactionType, EntryType


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    password: str  = Field(min_length=8)

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    created_at: datetime
    model_config = {"from_attributes": True}

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Accounts ──────────────────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    currency: str = Field(default="USD", max_length=3)

class AccountOut(BaseModel):
    id: int
    account_no: str
    currency: str
    balance: Decimal
    status: AccountStatus
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Transactions ──────────────────────────────────────────────────────────────

class TransferRequest(BaseModel):
    sender_account_no: str
    receiver_account_no: str
    amount: Decimal = Field(gt=0, decimal_places=4)
    currency: str = Field(default="USD", max_length=3)
    description: Optional[str] = None
    idempotency_key: str = Field(
        description="Unique key per payment attempt. Reusing the same key returns the original result.",
        min_length=8, max_length=64
    )

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

class DepositRequest(BaseModel):
    account_no: str
    amount: Decimal = Field(gt=0)
    idempotency_key: str = Field(min_length=8, max_length=64)

class TransactionOut(BaseModel):
    id: int
    idempotency_key: str
    type: TransactionType
    status: TransactionStatus
    amount: Decimal
    currency: str
    sender_id: Optional[int]
    receiver_id: Optional[int]
    description: Optional[str]
    failure_reason: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    model_config = {"from_attributes": True}


# ── Ledger ────────────────────────────────────────────────────────────────────

class LedgerEntryOut(BaseModel):
    id: int
    transaction_id: int
    account_id: int
    entry_type: EntryType
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    created_at: datetime
    model_config = {"from_attributes": True}
