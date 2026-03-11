from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.database import engine, Base
from app.routers import auth, accounts, transactions, ledger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="PayCore API",
    description="A production-style payments and ledger API simulating core fintech banking operations.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,         prefix="/api/v1/auth",         tags=["Authentication"])
app.include_router(accounts.router,     prefix="/api/v1/accounts",     tags=["Accounts"])
app.include_router(transactions.router, prefix="/api/v1/transactions",  tags=["Transactions"])
app.include_router(ledger.router,       prefix="/api/v1/ledger",        tags=["Ledger"])

@app.get("/health")
async def health():
    return {"status": "ok", "service": "PayCore API v1.0"}
