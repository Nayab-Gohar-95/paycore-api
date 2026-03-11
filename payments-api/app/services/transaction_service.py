"""
transaction_service.py
─────────────────────
The heart of the payments engine. Handles:
  1. Idempotency  — same key → same result, no double-processing
  2. Balance checks — insufficient funds → FAILED, never negative balance
  3. Double-entry bookkeeping — every transfer = 1 DEBIT + 1 CREDIT
  4. Atomicity — everything inside a single DB transaction (rollback on any error)
  5. Audit trail — LedgerEntry rows are immutable and never deleted
"""

from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.finance import (
    Account, Transaction, LedgerEntry,
    TransactionStatus, TransactionType, EntryType, AccountStatus
)
from app.schemas.schemas import TransferRequest, DepositRequest


async def _get_account_by_no(db: AsyncSession, account_no: str) -> Account:
    result = await db.execute(
        select(Account).where(Account.account_no == account_no).with_for_update()
        # with_for_update() → row-level lock prevents race conditions
        # (two concurrent transfers from the same account)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account {account_no} not found")
    if account.status != AccountStatus.ACTIVE:
        raise HTTPException(status_code=400, detail=f"Account {account_no} is {account.status}")
    return account


async def process_transfer(
    db: AsyncSession,
    payload: TransferRequest,
    initiating_user_id: int,
) -> Transaction:
    """
    Transfer funds between two accounts.
    Enforces: ownership, sufficient balance, idempotency, double-entry ledger.
    """

    # ── 1. Idempotency check ────────────────────────────────────────────────
    existing = await db.execute(
        select(Transaction).where(Transaction.idempotency_key == payload.idempotency_key)
    )
    existing_txn = existing.scalar_one_or_none()
    if existing_txn:
        # Return original result — do NOT process again
        return existing_txn

    # ── 2. Load & lock accounts ─────────────────────────────────────────────
    sender   = await _get_account_by_no(db, payload.sender_account_no)
    receiver = await _get_account_by_no(db, payload.receiver_account_no)

    # ── 3. Ownership check ──────────────────────────────────────────────────
    if sender.owner_id != initiating_user_id:
        raise HTTPException(status_code=403, detail="You do not own the sender account")

    if sender.id == receiver.id:
        raise HTTPException(status_code=400, detail="Cannot transfer to the same account")

    if sender.currency != receiver.currency:
        raise HTTPException(status_code=400, detail="Currency mismatch between accounts")

    # ── 4. Create transaction record (PENDING) ──────────────────────────────
    txn = Transaction(
        idempotency_key = payload.idempotency_key,
        type            = TransactionType.TRANSFER,
        status          = TransactionStatus.PENDING,
        amount          = payload.amount,
        currency        = payload.currency,
        sender_id       = sender.id,
        receiver_id     = receiver.id,
        description     = payload.description,
    )
    db.add(txn)
    await db.flush()  # get txn.id without committing

    # ── 5. Sufficient funds check ───────────────────────────────────────────
    if sender.balance < payload.amount:
        txn.status = TransactionStatus.FAILED
        txn.failure_reason = f"Insufficient funds. Balance: {sender.balance}, Required: {payload.amount}"
        await db.commit()
        return txn

    # ── 6. Double-entry bookkeeping ─────────────────────────────────────────
    # Rule: sum of all debits must equal sum of all credits (always balanced)

    sender_balance_before   = sender.balance
    receiver_balance_before = receiver.balance

    sender.balance   -= payload.amount   # DEBIT sender
    receiver.balance += payload.amount   # CREDIT receiver

    # Immutable ledger entries
    debit_entry = LedgerEntry(
        transaction_id = txn.id,
        account_id     = sender.id,
        entry_type     = EntryType.DEBIT,
        amount         = payload.amount,
        balance_before = sender_balance_before,
        balance_after  = sender.balance,
    )
    credit_entry = LedgerEntry(
        transaction_id = txn.id,
        account_id     = receiver.id,
        entry_type     = EntryType.CREDIT,
        amount         = payload.amount,
        balance_before = receiver_balance_before,
        balance_after  = receiver.balance,
    )
    db.add(debit_entry)
    db.add(credit_entry)

    # ── 7. Complete ──────────────────────────────────────────────────────────
    txn.status       = TransactionStatus.COMPLETED
    txn.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(txn)
    return txn


async def process_deposit(
    db: AsyncSession,
    payload: DepositRequest,
    initiating_user_id: int,
) -> Transaction:
    """Deposit funds into an account (e.g. from an external source)."""

    # Idempotency
    existing = await db.execute(
        select(Transaction).where(Transaction.idempotency_key == payload.idempotency_key)
    )
    if existing.scalar_one_or_none():
        return existing.scalar_one_or_none()

    account = await _get_account_by_no(db, payload.account_no)
    if account.owner_id != initiating_user_id:
        raise HTTPException(status_code=403, detail="You do not own this account")

    txn = Transaction(
        idempotency_key = payload.idempotency_key,
        type            = TransactionType.DEPOSIT,
        status          = TransactionStatus.PENDING,
        amount          = payload.amount,
        currency        = account.currency,
        receiver_id     = account.id,
    )
    db.add(txn)
    await db.flush()

    balance_before  = account.balance
    account.balance += payload.amount

    db.add(LedgerEntry(
        transaction_id = txn.id,
        account_id     = account.id,
        entry_type     = EntryType.CREDIT,
        amount         = payload.amount,
        balance_before = balance_before,
        balance_after  = account.balance,
    ))

    txn.status       = TransactionStatus.COMPLETED
    txn.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(txn)
    return txn
