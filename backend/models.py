from sqlalchemy import Column, Integer, String, LargeBinary, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import json
import re

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    avatar = Column(LargeBinary)  # Binary data for the user's avatar image
    nickname = Column(String)  # Nickname for the user
    description = Column(Text)  # Description for the user profile
    role = Column(String)  # Role of the user (user, admin, author, etc.)
    tags = Column(String)  # Tags associated with the user (serialized as a string)
    social_links = Column(String)  # Social links associated with the user (serialized as a string)
    favorites = relationship("Favorite", back_populates="user")  # Relationship with Favorite model

class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))  # Foreign key relationship with users table
    manga_id = Column(Integer, ForeignKey('mangadb.id'))  # Foreign key relationship with mangadb table
    user = relationship("User", back_populates="favorites")  # Relationship with User model


class MangaDB(Base):
    __tablename__ = "mangadb"

    id = Column(Integer, primary_key=True, index=True)
    cover = Column(LargeBinary)  # Binary data for the cover image of manga
    name = Column(String, unique=False, index=True)  # manga name
    description = Column(Text)  # manga description
    tags = Column(String)  # tags for the manga (serialized as a string)
    manga_type = Column(String)  # type for the manga
    slug = Column(String, unique=True, index=True)  # Slug for URL

    def set_tags(self, tags):
        self.tags = json.dumps(tags)

    def get_tags(self):
        try:
            if self.tags:
                # Split the string into a list of tags
                return [tag.strip() for tag in self.tags.split(',')]
            else:
                return []
        except json.JSONDecodeError:
            return []

    @staticmethod
    def generate_slug(name):
        # Remove special characters, convert spaces to hyphens, and convert to lowercase
        slug = re.sub(r"[^\w\s-]", "", name).strip().lower()
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug