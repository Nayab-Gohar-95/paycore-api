# PayCore API 

A production-style **payments and ledger backend** simulating core fintech banking operations — built as a portfolio project to demonstrate backend engineering skills relevant to financial systems.

> Built with FastAPI · PostgreSQL · Docker · SQLAlchemy 2.0 (async) · JWT Auth



##  Why I Built This

Payments infrastructure is one of the most technically demanding domains in software engineering. I built PayCore to learn and demonstrate the core concepts that underpin real banking and payments systems — double-entry bookkeeping, idempotency, atomic transactions, and immutable audit trails — using a production-style tech stack.



##  Architecture

```
POST /transfer
      │
      ▼
┌─────────────────┐
│ Idempotency     │  Same key? → return original result (no double-charge)
│ Check           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Balance         │  Insufficient funds? → mark FAILED, never go negative
│ Check           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Double-Entry    │  DEBIT sender + CREDIT receiver (atomic, single DB txn)
│ Bookkeeping     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Immutable       │  Permanent audit trail — entries never updated/deleted
│ Ledger          │
└─────────────────┘
```

---

##  Key Fintech Concepts Implemented

### 1. Double-Entry Bookkeeping
Every transaction creates exactly **two ledger entries**:
- **DEBIT** from the sender (balance decreases)
- **CREDIT** to the receiver (balance increases)

The sum of all debits always equals the sum of all credits — the mathematical foundation of all accounting systems.

### 2. Idempotency Keys
If a client retries a failed request (timeout, network error), the API returns the **original result** instead of processing the payment again. This prevents double-charging — a critical requirement in production payments systems.

```json
POST /api/v1/transactions/transfer
{
  "idempotency_key": "order-9fa2b3c4",
  "sender_account_no": "1234567890123456",
  "receiver_account_no": "9876543210987654",
  "amount": "250.00"
}
```

### 3. Atomic Transactions
All database operations for a transfer (balance update + ledger entries) execute inside a **single DB transaction**. Any failure rolls everything back — balances are never partially updated.

### 4. Immutable Audit Ledger
`LedgerEntry` rows are **never updated or deleted**. Every balance change is permanently recorded with `balance_before` and `balance_after` — a regulatory requirement in financial systems.

### 5. Row-Level Locking
Concurrent transfers from the same account use `SELECT ... FOR UPDATE` to acquire row-level locks, preventing race conditions that could corrupt balances.

---

##  Quick Start

**Prerequisites:** Docker Desktop installed and running.

```bash
# 1. Clone the repo
git clone https://github.com/Nayab-Gohar-95/paycore-api.git
cd paycore-api

# 2. Start PostgreSQL + API
docker-compose up --build

# 3. Open interactive API docs
# Navigate to: http://localhost:8000/docs
```

### Test the full flow in Swagger UI:
1. `POST /auth/register` — create a user
2. `POST /auth/login` — get JWT token → click **Authorize **
3. `POST /accounts/` — create two accounts
4. `POST /transactions/deposit` — fund account 1
5. `POST /transactions/transfer` — transfer to account 2
6. `GET /ledger/{account_no}` — view the immutable audit trail

---

##  API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register a new user |
| POST | `/api/v1/auth/login` | Login, receive JWT token |
| POST | `/api/v1/accounts/` | Create a new account |
| GET  | `/api/v1/accounts/` | List your accounts |
| POST | `/api/v1/transactions/deposit` | Deposit funds |
| POST | `/api/v1/transactions/transfer` | Transfer between accounts |
| GET  | `/api/v1/transactions/` | List your transactions |
| GET  | `/api/v1/ledger/{account_no}` | View immutable ledger / audit trail |
| GET  | `/health` | Health check |

---

##  Data Model

```
users
  └── accounts        (one user → many accounts)
        └── transactions    (sender / receiver)
              └── ledger_entries   (2 per transaction: DEBIT + CREDIT)
```

Each `Transaction` produces exactly **2 LedgerEntry rows** — one DEBIT, one CREDIT — preserving full balance history.

---

##  Tech Stack

| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI (async) |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Auth | JWT / OAuth2 (python-jose + passlib) |
| Validation | Pydantic v2 |
| Containerization | Docker + Docker Compose |

---

##  Project Structure

```
paycore-api/
├── app/
│   ├── main.py                      # FastAPI app + lifespan
│   ├── core/
│   │   ├── config.py                # Pydantic settings
│   │   ├── database.py              # Async SQLAlchemy engine
│   │   └── security.py              # JWT auth helpers
│   ├── models/
│   │   ├── user.py                  # User model
│   │   └── finance.py               # Account, Transaction, LedgerEntry
│   ├── schemas/
│   │   └── schemas.py               # Pydantic request/response schemas
│   ├── services/
│   │   └── transaction_service.py   # Core payments logic
│   └── routers/
│       ├── auth.py
│       ├── accounts.py
│       ├── transactions.py
│       └── ledger.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

##  Author

**Nayab Gohar** — CS student at Information Technology University (ITU), Lahore  
 [GitHub](https://github.com/Nayab-Gohar-95)
