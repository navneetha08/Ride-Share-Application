from sqlalchemy import Column, Integer, Sequence, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from flask_sqlalchemy_session import current_session
from sqlalchemy import create_engine
# from database_rides import Ride, RideUsers
from datetime import datetime


Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False)
    password = Column(String(40), nullable=False)
    # ride = relationship("Ride", cascade="all,delete")
    # ride_users = relationship("RideUsers", cascade="all,delete")

    @staticmethod
    def getByUsername(username):
        return current_session.query(User).filter(User.username == username).one_or_none()
    @staticmethod
    def getUsers():
        return current_session.query(User).all()

    def store(self):
        current_session.add(self)
        current_session.commit()

    def delete(self):
        current_session.delete(self)
        current_session.commit()


