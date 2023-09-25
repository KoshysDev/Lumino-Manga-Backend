import os
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from dotenv import load_dotenv
from models import User

# Load environment variables from .env
load_dotenv()

# Load database URL from .env
DATABASE_URL = os.getenv('DATABASE_URL')

app = FastAPI()

# SQLAlchemy database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@app.post("/register")
def register_user(username: str, email: str, password: str):
    # Check if the username and email are unique
    session = SessionLocal()
    existing_user = session.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=400, detail="Username or email already registered"
        )

    # Hash the password before storing it
    hashed_password = pwd_context.hash(password)

    # Create a new user
    new_user = User(username=username, email=email, hashed_password=hashed_password)

    session.add(new_user)
    session.commit()
    session.close()
    return {"message": "User registered successfully"}
