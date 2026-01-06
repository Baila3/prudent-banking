from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import engine, Base, get_db, Transaction, User
from sqlalchemy import func
import google.generativeai as genai
import os

# Configure the AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash-latest')

def get_ai_advice(user_email, risk_profile, total_spent, top_category, category_amount):
    prompt = f"""
    You are a professional financial advisor. 
    The user ({user_email}) has a {risk_profile} risk tolerance.
    This month, they spent a total of ${total_spent}.
    Their highest spending category was {top_category} at ${category_amount}.
    
    Provide:
    1. A friendly one-sentence summary of their spending.
    2. One specific tip to reduce spending in {top_category}.
    3. One investment suggestion suitable for a {risk_profile} investor.
    Keep the tone encouraging and concise.
    """
    
    response = model.generate_content(prompt)
    return response.text

Base.metadata.create_all(bind=engine)

app = FastAPI()


class TransactionCreate(BaseModel):
    amount: float
    category: str
    merchant: str
    user_id: int
class UserCreate(BaseModel):
    email: str
    risk_tolerance: str


# --- ROUTES ---

@app.get("/")
def health_check():
    return {"status": "Database connected and tables created!"}

@app.get("/users/")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()


@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    return {"message": "Successfully connected to the database session!"}

@app.get("/users/{user_id}/advice")
def get_fin_advice(user_id: int, db: Session = Depends(get_db)):
    user = db .query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    total_spent_raw = db.query(func.sum(Transaction.amount)).filter(Transaction.user_id == user_id).scalar()
    total_spent = float(total_spent_raw) if total_spent_raw is not None else 0.0

    top_category = db.query(Transaction.category, func.sum(Transaction.amount).label('cat_total'))\
        .filter(Transaction.user_id == user_id)\
        .group_by(Transaction.category)\
        .order_by(func.sum(Transaction.amount).desc()).first()

    top_cat = top_category[0] if top_category else "None"
    top_amount = top_category[1] if top_category else 0

    #Call to AI engine
    ai_response = get_ai_advice(
        user.email,
        user.risk_tolerance,
        total_spent,
        top_cat,
        top_amount
    )

    return {
        "user_email": user.email,
        "monthly_summary": {
            "total_spent": total_spent,
            "primary_expense": top_category[0] if top_category else "None"
        },
        "tips": tips,
        "investment_strategy": ai_response
    }

@app.post("/users/")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(
        email = user.email, 
        risk_tolerance = user.risk_tolerance
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Create new transaction
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

# View transactions
@app.get("/transactions/")
def get_transactions(db: Session = Depends(get_db)):
    # Returns all rows from the 'transactions' table
    return db.query(Transaction).all()