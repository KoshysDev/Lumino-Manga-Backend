import base64
import os
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    Query,
    Request,
    File,
    UploadFile,
    Form,
)
from datetime import datetime, timedelta
from requests import Session, session
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from models import User, MangaDB
import jwt
from typing import Optional

# this file must be refactored, after i done main job

# Load environment variables from .env
load_dotenv()

# Load database URL from .env
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can replace "*" with frontend URL
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
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"


@app.post("/register/")
def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    avatar: UploadFile = File(None),
    nickname: str = Form(None),
    description: str = Form(None),
    role: str = Form(None),
    tags: str = Form(None),
    social_links: str = Form(None),
):
    # Check if the username and email are unique
    session = SessionLocal()
    existing_user = (
        session.query(User)
        .filter((User.username == username) | (User.email == email))
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=400, detail="Username or email already registered"
        )

    # Hash the password before storing it
    hashed_password = pwd_context.hash(password)

    # Create a new user
    new_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        nickname=nickname or username,  # Set the nickname to username if not provided
        description=description,
        role=role,
        tags=tags,
        social_links=social_links,
    )

    # Process and store avatar image if provided
    if avatar:
        new_user.avatar = avatar.file.read()

    session.add(new_user)
    session.commit()
    session.close()

    return {"message": "User registered successfully"}


# Retrieve the user from the database by username
@app.post("/login/")
def login_user(request: Request, username: str = Form(...), password: str = Form(...)):
    session = SessionLocal()
    user = session.query(User).filter(User.username == username).first()  # type: ignore
    session.close()

    if not user:
        raise HTTPException(status_code=401, detail="Username or password is incorrect")

    # Verify the password
    if not pwd_context.verify(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Username or password is incorrect")

    client_host = request.client.host  # type: ignore
    # Generate a JWT token based on user.id
    access_token = create_access_token(user.id)
    return {
        "client_host": client_host,
        "access_token": access_token,
        "token_type": "bearer",
    }


# Function to get the current user based on the JWT token
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload["sub"]
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:  # type: ignore
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
        "avatar": (
            base64.b64encode(user.avatar).decode("utf-8") if user.avatar else None
        ),  # Encode avatar image to base64 if available
        "nickname": user.nickname,
        "description": user.description,
        "role": user.role,
        "tags": user.tags,
        "social_links": user.social_links,
        # Add other fields as needed
    }

    return user_data


@app.put("/update_profile")
def update_user_profile(
    nickname: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    social_links: Optional[str] = Form(None),
    current_user: int = Depends(get_current_user),
):
    session = SessionLocal()
    user = session.query(User).filter(User.id == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update user details
    if nickname is not None:
        user.nickname = nickname
    if description is not None:
        user.description = description
    if avatar:
        user.avatar = avatar.file.read()
    if email is not None:
        user.email = email
    if password is not None:
        hashed_password = pwd_context.hash(password)
        user.hashed_password = hashed_password
    if role is not None:
        user.role = role
    if tags is not None:
        user.tags = tags
    if social_links is not None:
        user.social_links = social_links

    session.commit()
    session.close()

    return {"message": "User profile updated successfully"}


# manga section - refactor after
# Update the create and update operations to calculate and store the slug
@app.post("/create_manga/")
def create_manga(
    name: str = Form(...),
    description: str = Form(...),
    tags: str = Form(...),
    manga_type: str = Form(...),
    cover_image: UploadFile = File(...),
    current_user: int = Depends(get_current_user),
):
    # Read the binary data of the image
    cover_data = cover_image.file.read()

    # Create manga in the database
    session = SessionLocal()
    manga = MangaDB(
        name=name,
        description=description,
        tags=tags,
        manga_type=manga_type,
        cover=cover_data,
        slug=MangaDB.generate_slug(name),  # Calculate and store the slug
    )
    session.add(manga)
    session.commit()
    session.close()

    return {"message": "Manga uploaded successfully"}


# Endpoint for geting manga by id
@app.get("/manga/by_id/{manga_id}")
def get_manga(manga_id: int):
    session = SessionLocal()
    manga = (
        session.query(MangaDB).filter(MangaDB.id == manga_id).first()  # type: ignore
    )  # type: ignore
    session.close()

    if not manga:
        raise HTTPException(status_code=404, detail="Manga not found")

    # Convert the manga object to a dictionary
    manga_data = {
        "id": manga.id,
        "name": manga.name,
        "description": manga.description,
        "tags": manga.get_tags(),
        "manga_type": manga.manga_type,
        "cover_image": (
            base64.b64encode(manga.cover).decode("utf-8") if manga.cover else None
        ),
    }

    return manga_data


from fastapi import Path


@app.get("/manga/{slug}")
def get_manga_by_slug(slug: str = Path(...)):
    session = SessionLocal()
    manga = (
        session.query(MangaDB).filter(MangaDB.slug == slug).first()  # type: ignore
    )  # type: ignore
    session.close()

    if not manga:
        raise HTTPException(status_code=404, detail="Manga not found")

    # Convert the manga object to a dictionary
    manga_data = {
        "id": manga.id,
        "name": manga.name,
        "description": manga.description,
        "tags": manga.get_tags(),
        "manga_type": manga.manga_type,
        "cover_image": (
            base64.b64encode(manga.cover).decode("utf-8") if manga.cover else None
        ),
    }

    return manga_data


# Endpoint to get the total number of manga
@app.get("/manga_count")
def get_total_manga_count():
    session = SessionLocal()
    total_count = session.query(MangaDB).count()
    session.close()
    return JSONResponse(content={"count": total_count})


# get all manga by pagination, using offset(how many to skip) and limit(how many to display)
@app.get("/manga")
def get_manga_list(page: int = Query(1, ge=1), limit: int = Query(10, le=100)):
    session = SessionLocal()

    # Calculate the offset based on the page and limit
    offset = (page - 1) * limit

    # Query the database for manga with pagination
    manga_list = session.query(MangaDB).offset(offset).limit(limit).all()  # type: ignore

    session.close()

    # Convert the manga objects to a list of dictionaries
    manga_data_list = []
    for manga in manga_list:
        manga_data = {
            "id": manga.id,
            "name": manga.name,
            "description": manga.description,
            "tags": manga.get_tags(),
            "manga_type": manga.manga_type,
            "cover_image": (
                base64.b64encode(manga.cover).decode("utf-8") if manga.cover else None
            ),
        }
        manga_data_list.append(manga_data)

    return manga_data_list


# Endpoint for updating manga by id
@app.put("/update_manga/{manga_id}")
def update_manga(
    manga_id: int,
    name: str = Form(...),
    description: str = Form(...),
    tags: str = Form(...),
    manga_type: str = Form(...),
    cover_image: UploadFile = File(...),
    current_user: int = Depends(get_current_user),
):
    # Read the binary data of the image
    cover_data = cover_image.file.read()

    # Update manga in the database
    session = SessionLocal()
    manga = (
        session.query(MangaDB).filter(MangaDB.id == manga_id).first()  # type: ignore
    )  # type: ignore

    if not manga:
        raise HTTPException(status_code=404, detail="Manga not found")

    # Update manga properties
    manga.name = name
    manga.description = description
    manga.tags = tags
    manga.manga_type = manga_type
    manga.cover = cover_data
    manga.slug = MangaDB.generate_slug(name)  # Recalculate and store the slug

    session.commit()
    session.close()

    return {"message": "Manga updated successfully"}


# Create a JWT token with the user's username as the subject (sub)
def create_access_token(user_id: int):
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(days=30),  # Expiration time
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token
