
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Sequence

import database

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    discord_tag = Column(String(50), primary_key=True)
    pincode = Column(String(6))
    min_age = Column(Integer)

    def __repr__(self):
        return f'<User(discord_tag=\'{self.discord_tag}\', pincode=\'{self.pincode}\')>'


Base.metadata.create_all(database.engine)
