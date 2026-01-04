from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
# Import the Transaction class and the database setup
from database import engine, Base, get_db, Transaction 

# This creates the tables in Postgres if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI()

# --- SCHEMAS (Pydantic) ---
# This defines the data structure the API expects to receive
class TransactionCreate(BaseModel):
    amount: float
    category: str
    merchant: str
    user_id: int

# --- ROUTES ---

@app.get("/")
def health_check():
    return {"status": "Database connected and tables created!"}

@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    return {"message": "Successfully connected to the database session!"}

# Create a new transaction
@app.post("/transactions/")
def create_transaction(transaction: TransactionCreate, db: Session = Depends(get_db)):
    db_transaction = Transaction(
        amount=transaction.amount,
        category=transaction.category,
        merchant=transaction.merchant,
        user_id=transaction.user_id
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return {"status": "success", "transaction_id": db_transaction.id}

# View all transactions
@app.get("/transactions/")
def get_transactions(db: Session = Depends(get_db)):
    # Returns all rows from the 'transactions' table
    return db.query(Transaction).all()