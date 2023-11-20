import os
from fastapi.security import OAuth2PasswordBearer
from fastapi import FastAPI, HTTPException, Depends, Request
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from models import User, MangaDB
import jwt

#this file must be refactored, after i done main job

# Load environment variables from .env
load_dotenv()

# Load database URL from .env
DATABASE_URL = os.getenv('DATABASE_URL')

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can replace "*" with your frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
)

# SQLAlchemy database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Create an instance of OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# Define JWT settings
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = "HS256"

@app.get("/register/username={username}&email={email}&password={password}")
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
@app.get("/login/username={username}&password={password}")
def login_user(username: str, password: str, request: Request):
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
    
    client_host = request.client.host
    # Generate a JWT token based on user.id
    access_token = create_access_token(user.id)
    return {"client_host": client_host, "access_token": access_token, "token_type": "bearer"}

# Function to get the current user based on the JWT token
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload["sub"]
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Could not validate token")

# Endpoint to get user profile
@app.get("/profile")
def get_user_profile(current_user: int = Depends(get_current_user)):
    session = SessionLocal()
    user = session.query(User).filter(User.id == current_user).first()
    session.close()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Convert the user object to a dictionary
    user_data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        # Add other fields as needed
    }
    
    return user_data

# Create a JWT token with the user's username as the subject (sub)
def create_access_token(user_id: int):
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=1)  # Expiration time
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token