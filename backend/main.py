import os
from fastapi import FastAPI, HTTPException, Depends
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from dotenv import load_dotenv
from models import User
import jwt

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

# Define JWT settings
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = "HS256"

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
    
    # Generate a JWT token
    access_token = create_access_token(data={"sub": username})
    return {"access_token": access_token, "token_type": "bearer"}

# Create a JWT token with the user's username as the subject (sub)
def create_access_token(data: dict):
    # Calculate the expiration time (one month from now)
    expires = datetime.utcnow() + timedelta(days=30)

    # Add the "exp" claim to the token's payload
    data["exp"] = expires

    # Encode the token with the expiration time
    token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    return token