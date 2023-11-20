from sqlalchemy import Column, Integer, String, LargeBinary, Text
from sqlalchemy.ext.declarative import declarative_base
import json

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class MangaDB(Base):
    __tablename__ = "mangadb"

    id = Column(Integer, primary_key=True, index=True)
    cover = Column(LargeBinary)  # Binary data for the cover image of manga
    name = Column(String, unique=False, index=True)  # manga name
    description = Column(Text)  # manga description
    tags = Column(String)  # tags for the manga (serialized as a string)
    manga_type = Column(String)  # type for the manga

    def set_tags(self, tags):
        self.tags = json.dumps(tags)

    def get_tags(self):
        return json.loads(self.tags) if self.tags else []
