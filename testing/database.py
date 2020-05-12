from datetime import datetime
import sqlite3

conn = sqlite3.connect('rideshare.db')


class Ride:
    __tablename__ = 'ride'

    def __init__(self, created_by, source, destination, timestamp, rideId=None):
        self.created_by = created_by
        self.source = source
        self.destination = destination
        self.timestamp = timestamp
        self.rideId = rideId

    def store(self):
        c = conn.cursor()
        c.execute(
            'INSERT INTO ride (created_by, source, destination, timestamp) VALUES (?, ?, ?, ?)', [self.created_by,
                                                                                                  self.source, self.destination, self.timestamp])

        self.rideId = c.lastrowid

        conn.commit()
        return self.rideId

    def delete(self):
        c = conn.cursor()
        c.execute(
            'DELETE FROM ride WHERE rideId = ?', [self.rideId])
        conn.commit()

    @staticmethod
    def getRides():
        rides = list()
        c = conn.execute(
            "SELECT rideId, created_by, source, destination, timestamp from ride")

        for row in c:
            r = Ride(rideId=row[0], created_by=row[1], source=row[
                     2], destination=row[3], timestamp=row[4])
            rides.append(r)
        return rides

    @staticmethod
    def getByRideId(rideId):
        c = conn.execute(
            "SELECT rideId, created_by, source, destination, timestamp from ride WHERE rideId = ?", [rideId])
        row = c.fetchone()
        if (row is None):
            return None

        r = Ride(rideId=row[0], created_by=row[1], source=row[
            2], destination=row[3], timestamp=row[4])
        return r

    @staticmethod
    def getByUsername(username):
        rides = list()
        c = conn.execute(
            "SELECT rideId, created_by, source, destination, timestamp from ride where created_by = ?", [username])

        for row in c:
            r = Ride(rideId=row[0], created_by=row[1], source=row[
                     2], destination=row[3], timestamp=row[4])
            rides.append(r)
        return rides

    @staticmethod
    def listBySource(source):
        rides = list()
        c = conn.execute(
            "SELECT rideId, created_by, source, destination, timestamp from ride where source = ?", [source])

        for row in c:
            r = Ride(rideId=row[0], created_by=row[1], source=row[
                     2], destination=row[3], timestamp=row[4])
            rides.append(r)
        return rides

    @staticmethod
    def listByDestination(destination):
        rides = list()
        c = conn.execute(
            "SELECT rideId, created_by, source, destination, timestamp from ride where destination = ?", [destination])

        for row in c:
            r = Ride(rideId=row[0], created_by=row[1], source=row[
                     2], destination=row[3], timestamp=row[4])
            rides.append(r)
        return rides

    @staticmethod
    def listUpcomingRides(source, destination):
        rides = list()
        c = conn.execute(
            "SELECT rideId, created_by, source, destination, timestamp from ride where source = ? and destination = ? and timestamp >= ?", [source, destination, datetime.now()])

        for row in c:
            r = Ride(rideId=row[0], created_by=row[1], source=row[
                     2], destination=row[3], timestamp=row[4])
            rides.append(r)
        return rides
        return current_session.query(Ride).filter(Ride.source == source).filter(Ride.destination == destination).filter(Ride.timestamp >= datetime.now()).all()

    @staticmethod
    def getRideId(created_by, source, destination, timestamp):
        c = conn.execute(
            "SELECT rideId, created_by, source, destination, timestamp from ride where source = ? and destination = ? and timestamp = ?", [source, destination, timestamp])
        row = c.fetchone()
        if (row is None):
            return None

        r = Ride(rideId=row[0], created_by=row[1], source=row[
            2], destination=row[3], timestamp=row[4])
        return r


class RideUsers():
    __tablename__ = 'ride_users'
    # id = Column(Integer, primary_key=True, autoincrement=True)
    # rideId = Column(Integer, nullable=False)
    # username = Column(String(80), ForeignKey(Ride.created_by), nullable=False)

    def __init__(self, username, ride_id, id=None):
        self.id = id
        self.username = username
        self.rideId = ride_id

    @staticmethod
    def getByRideId(rideId):
        users = list()
        c = conn.execute(
            "SELECT id, rideId, username from ride_users")

        for row in c:
            u = RideUsers(id=row[0], ride_id=row[1], username=row[
                2])
            users.append(u)
        return users

    def store(self):
        c = conn.cursor()
        c.execute(
            'INSERT INTO ride_users (rideId, username) VALUES (?, ?)', [self.rideId,
                                                                        self.username])

        self.id = c.lastrowid

        conn.commit()
        return self.id

    def delete(self):
        c = conn.cursor()
        c.execute(
            'DELETE FROM ride_users WHERE id = ?', [self.id])
        conn.commit()


class User():
    __tablename__ = 'user'
    # user_id = Column(Integer, primary_key=True, autoincrement=True)
    # username = Column(String(80), unique=True, nullable=False)
    # password = Column(String(40), nullable=False)
    # ride = relationship("Ride", cascade="all,delete")
    # ride_users = relationship("RideUsers", cascade="all,delete")

    def __init__(self, username, password, user_id=None):
        self.user_id = user_id
        self.username = username
        self.password = password

    @staticmethod
    def getByUsername(username):
        c = conn.execute(
            "SELECT user_id, username, password from user WHERE username = ?", [username])
        row = c.fetchone()
        if (row is None):
            return None

        u = User(user_id=row[0], username=row[1], password=row[
            2])
        return r

    @staticmethod
    def getUsers():
        users = list()
        c = conn.execute(
            "SELECT user_id, username, password from user")

        for row in c:
            u = User(user_id=row[0], username=row[1], password=row[
                     2])
            users.append(u)
        return users

    def store(self):
        c = conn.cursor()
        c.execute(
            'INSERT INTO user (username, password) VALUES (?, ?)', [self.username,
                                                                    self.password])

        self.user_id = c.lastrowid

        conn.commit()
        return self.user_id

    def delete(self):
        c = conn.cursor()
        c.execute(
            'DELETE FROM user WHERE user_id = ?', [self.user_id])
        conn.commit()
