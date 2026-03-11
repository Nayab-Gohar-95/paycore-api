from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, ForeignKey,
    Enum as SAEnum, Text, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class AccountStatus(str, enum.Enum):
    ACTIVE   = "ACTIVE"
    FROZEN   = "FROZEN"
    CLOSED   = "CLOSED"


class TransactionStatus(str, enum.Enum):
    PENDING   = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED    = "FAILED"
    REVERSED  = "REVERSED"


class TransactionType(str, enum.Enum):
    TRANSFER = "TRANSFER"
    DEPOSIT  = "DEPOSIT"
    WITHDRAW = "WITHDRAW"


class EntryType(str, enum.Enum):
    DEBIT  = "DEBIT"
    CREDIT = "CREDIT"


class Account(Base):
    __tablename__ = "accounts"

    id           = Column(Integer, primary_key=True, index=True)
    account_no   = Column(String(20), unique=True, nullable=False, index=True)
    owner_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    currency     = Column(String(3), default="USD", nullable=False)
    balance      = Column(Numeric(precision=18, scale=4), default=0, nullable=False)
    status       = Column(SAEnum(AccountStatus), default=AccountStatus.ACTIVE, nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())

    owner        = relationship("User", back_populates="accounts")
    ledger_entries = relationship("LedgerEntry", back_populates="account")


class Transaction(Base):
    """
    Represents a single payment intent (e.g. a transfer between two accounts).
    Each Transaction produces two LedgerEntry rows — one DEBIT, one CREDIT.
    This is double-entry bookkeeping, the foundation of all financial systems.
    """
    __tablename__ = "transactions"

    id               = Column(Integer, primary_key=True, index=True)
    idempotency_key  = Column(String(64), unique=True, nullable=False, index=True)
    # ^ Idempotency key: if the same request is retried (network failure, timeout),
    #   we return the original result instead of processing twice. Critical in payments.

    type             = Column(SAEnum(TransactionType), nullable=False)
    status           = Column(SAEnum(TransactionStatus), default=TransactionStatus.PENDING)
    amount           = Column(Numeric(precision=18, scale=4), nullable=False)
    currency         = Column(String(3), default="USD")
    sender_id        = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    receiver_id      = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    description      = Column(Text, nullable=True)
    failure_reason   = Column(Text, nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    completed_at     = Column(DateTime(timezone=True), nullable=True)

    ledger_entries   = relationship("LedgerEntry", back_populates="transaction")


class LedgerEntry(Base):
    """
    Immutable audit log. Every transaction produces exactly TWO entries:
      - DEBIT  from sender   (balance decreases)
      - CREDIT to receiver   (balance increases)
    Ledger entries are NEVER updated or deleted. This is the source of truth.
    """
    __tablename__ = "ledger_entries"

    id             = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    account_id     = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    entry_type     = Column(SAEnum(EntryType), nullable=False)   # DEBIT or CREDIT
    amount         = Column(Numeric(precision=18, scale=4), nullable=False)
    balance_before = Column(Numeric(precision=18, scale=4), nullable=False)
    balance_after  = Column(Numeric(precision=18, scale=4), nullable=False)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    transaction    = relationship("Transaction", back_populates="ledger_entries")
    account        = relationship("Account", back_populates="ledger_entries")

    __table_args__ = (
        Index("ix_ledger_account_created", "account_id", "created_at"),
    )
