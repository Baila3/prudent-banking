from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import engine, Base, get_db, Transaction, User
from sqlalchemy import func

import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def get_LLM_advice(user_email,risk_profile, total_spent, top_category, category_amount):
    prompt = f"""
    you are a professional financial advisor.
    The user ({user_email}) has a ({risk_profile}) risk tolerance.
    This month they spent a total of ${total_spent}.
    Their highest spending category was {top_category} at ${category_amount}.

    Provide:
    1. a friendly one-sentence summary of their spending.
    2. one specific tip to reduce their spending in {top_category}.
    3. one investement solution suitable for a {risk_profile} investor.
    Keep tone encouraging and concise.
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
def get_advice(user_id: int, db: Session = Depends(get_db)):
    user = db .query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    total_spent_raw = db.query(func.sum(Transaction.amount)).filter(Transaction.user_id == user_id).scalar()
    total_spent = float(total_spent_raw) if total_spent_raw is not None else 0.0

    top_category = db.query(Transaction.category, func.sum(Transaction.amount).label('cat_total'))\
        .filter(Transaction.user_id == user_id)\
        .group_by(Transaction.category)\
        .order_by(func.sum(Transaction.amount).desc()).first()

    tips = []
    if top_category and top_category.cat_total > 500: #ex. of threshold
        tips.append(f"you spent ${top_category.cat_total} on {top_category.category}. A 10% reduction in spending could save you ${top_category.cat_total * 0.1:2f}!")

    invest_suggestion = ""
    if user.risk_tolerance == "Aggressive":
        invest_suggestion = "Based on your Aggressive profile, consider adding extra funds into High-Growth Tech ETF (like QQQ)."
    else:
        invest_suggestion = "Based on your Moderate profile, a diversified S&P 500 Index fund is your best bet this month"

    return {
        "user_email": user.email,
        "monthly_summary": {
            "total_spent": total_spent,
            "primary_expense": top_category[0] if top_category else "None"
        },
        "tips": tips,
        "investment_strategy": invest_suggestion
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