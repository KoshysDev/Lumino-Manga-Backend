import os
from fastapi import FastAPI, HTTPException, Depends
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

# Retrieve the user from the database by username
@app.post("/login")
def login_user(username: str, password: str):
    session = SessionLocal()
    user = session.query(User).filter(User.username == username).first()
    session.close()

    if not user:
        raise HTTPException(
            status_code=401, detail="Username or password is incorrect"
        )

    # Verify the password
    if not pwd_context.verify(password, user.hashed_password):
        raise HTTPException(
            status_code=401, detail="Username or password is incorrect"
        )

    # OAuth2 / JWT logic for login here

    return {"message": "Login successful"}

