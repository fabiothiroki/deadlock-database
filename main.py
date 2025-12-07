import os
import time
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from psycopg_pool import ConnectionPool
from psycopg.errors import DeadlockDetected

# Logger setup to see what's happening in the console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bank_api")

# Get DB connection string from Docker environment variable
DB_DSN = os.getenv("DB_DSN", "postgresql://user:password@localhost:5432/bank_db")

# Create a connection pool (better than opening a new connection every time)
pool = ConnectionPool(DB_DSN, open=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager: Opens DB pool on startup and closes on shutdown.
    """
    pool.open()
    yield
    pool.close()

app = FastAPI(lifespan=lifespan)

# --- Pydantic Models (Data Validation) ---
class TransferRequest(BaseModel):
    from_account: int
    to_account: int
    amount: int

# --- API Endpoints ---

@app.post("/reset")
def reset_database():
    """
    Resets the database for the start of the demo.
    Creates 2 accounts: 1 (Alice) and 2 (Bob) with $1000 each.
    """
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS accounts")
            cur.execute("""
                CREATE TABLE accounts (
                    id INT PRIMARY KEY,
                    name TEXT,
                    balance INT
                )
            """)
            cur.execute("INSERT INTO accounts (id, name, balance) VALUES (1, 'Alice', 1000)")
            cur.execute("INSERT INTO accounts (id, name, balance) VALUES (2, 'Bob', 1000)")
            conn.commit()
    return {"message": "Database reset. Alice (1) and Bob (2) have $1000."}


@app.post("/transfer/unsafe")
def transfer_unsafe(req: TransferRequest):
    """
    The BAD way to transfer money.
    Locks sender first, then receiver.
    If Alice pays Bob AND Bob pays Alice at the same time -> DEADLOCK.
    """
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # 1. Lock the sender's account
                # We MUST lock here to safely check if they have funds.
                cur.execute(
                    "SELECT balance FROM accounts WHERE id = %s FOR UPDATE", 
                    (req.from_account,)
                )
                current_balance = cur.fetchone()[0]

                if current_balance < req.amount:
                    raise HTTPException(status_code=400, detail="Insufficient funds")
                
                # ARTIFICIAL DELAY (Simulating latency)
                time.sleep(0.1) 

                # 2. Perform the Transfer
                cur.execute("UPDATE accounts SET balance = balance - %s WHERE id = %s", (req.amount, req.from_account))
                
                # --- THE TRAP IS HERE ---
                # This UPDATE statement implicitly tries to lock the receiver's row.
                # If Bob is the receiver, and Bob is running a transaction... deadlock.
                cur.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s", (req.amount, req.to_account))

                conn.commit()
                return {"status": "success", "msg": "Transfer complete"}

    except DeadlockDetected:
        # Postgres explicitly tells us a deadlock happened
        logger.error("DEADLOCK DETECTED! The transaction was killed.")
        raise HTTPException(
            status_code=500, 
            detail="Deadlock detected! The database killed this request to save itself."
        )


@app.post("/transfer/safe")
def transfer_safe(req: TransferRequest):
    """
    The GOOD way to transfer money.
    Implements 'Lock Ordering': Always lock the smaller ID first.
    """
    # Sort IDs to ensure consistent locking order
    # No matter who pays whom, we always lock Account 1 before Account 2
    first_lock_id = min(req.from_account, req.to_account)
    second_lock_id = max(req.from_account, req.to_account)

    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # 1. Lock accounts in fixed order
                logger.info(f"Safe Lock 1: {first_lock_id}")
                cur.execute("SELECT balance FROM accounts WHERE id = %s FOR UPDATE", (first_lock_id,))
                
                # --- Same delay to prove it works even with latency ---
                time.sleep(0.1) 
                
                logger.info(f"Safe Lock 2: {second_lock_id}")
                cur.execute("SELECT balance FROM accounts WHERE id = %s FOR UPDATE", (second_lock_id,))

                # 2. Check balance (logic needs to handle who is sending)
                # We need to re-fetch the sender's balance specifically to check funds
                cur.execute("SELECT balance FROM accounts WHERE id = %s", (req.from_account,))
                sender_balance = cur.fetchone()[0]

                if sender_balance < req.amount:
                    raise HTTPException(status_code=400, detail="Insufficient funds")

                # 3. Perform the Transfer
                cur.execute(
                    "UPDATE accounts SET balance = balance - %s WHERE id = %s", 
                    (req.amount, req.from_account)
                )
                cur.execute(
                    "UPDATE accounts SET balance = balance + %s WHERE id = %s", 
                    (req.amount, req.to_account)
                )
                
                conn.commit()
                return {"status": "success", "msg": "Safe Transfer complete"}
    except DeadlockDetected:
        # This should theoretically never happen in this endpoint
        logger.error("Deadlock in safe endpoint? Impossible!")
        raise HTTPException(status_code=500, detail="Deadlock detected")