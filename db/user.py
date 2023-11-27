import datetime

from sqlalchemy import Integer, Column, VARCHAR, DATE

from db.base import BaseModel


class User(BaseModel):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(VARCHAR(32), nullable=False)
    language = Column(VARCHAR(5), nullable=False)
    saved_movies = Column(VARCHAR(5))
    reg_date = Column(DATE)
    update_date = Column(DATE)

    def __str__(self) -> str:
        return f'User {self.username} with id {self.user_id} and language {self.language}'
