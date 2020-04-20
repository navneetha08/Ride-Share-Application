from sqlalchemy import Column, Integer, Sequence, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from flask_sqlalchemy_session import current_session
from sqlalchemy import create_engine
#from database_users import User
from datetime import datetime


Base = declarative_base()


class Ride(Base):
    __tablename__ = 'ride'
    rideId = Column(Integer, primary_key=True, autoincrement=True)
    created_by = Column(String(80), nullable=False)
    source = Column(Integer, nullable=False)
    destination = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    #ride_users = relationship("RideUsers", cascade="all,delete")

    def store(self):
        current_session.add(self)
        current_session.commit()
        return self.rideId

    def delete(self):
        current_session.delete(self)
        current_session.commit()
    @staticmethod
    def getRides():
        return current_session.query(Ride).all()
    @staticmethod
    def getByRideId(rideId):
        return current_session.query(Ride).get(rideId)

    @staticmethod
    def getByUsername(username):
        return current_session.query(Ride).filter(Ride.created_by == username).one_or_none()

    @staticmethod
    def listBySource(source):
        return current_session.query(Ride).filter(Ride.source == source).all()

    @staticmethod
    def listByDestination(destination):
        return current_session.query(Ride).filter(Ride.destination == destination).all()

    @staticmethod
    def listUpcomingRides(source, destination):
        return current_session.query(Ride).filter(Ride.source == source).filter(Ride.destination == destination).filter(Ride.timestamp >= datetime.now()).all()

    @staticmethod
    def getRideId(created_by, source, destination, timestamp):
        return current_session.query(Ride).filter(Ride.created_by == created_by).filter(Ride.source == source).filter(Ride.destination == destination).filter(Ride.timestamp == timestamp).one()


class RideUsers(Base):
    __tablename__ = 'ride_users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    rideId = Column(Integer,nullable=False)
    username = Column(String(80), ForeignKey(Ride.created_by),nullable=False)

    @staticmethod
    def getByRideId(rideId):
        return current_session.query(RideUsers).filter(RideUsers.rideId == rideId).all()

    def store(self):
        current_session.add(self)
        current_session.commit()
        return self.rideId

    def delete(self):
        current_session.delete(self)
        current_session.commit()
