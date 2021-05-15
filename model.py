
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Sequence

import database

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    discord_tag = Column(String(50), primary_key=True)
    district = Column(String(255))
    min_age = Column(Integer)


Base.metadata.create_all(database.engine)
