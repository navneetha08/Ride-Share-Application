import hashlib

from werkzeug.exceptions import BadRequest
from database import User
from database import Ride
from datetime import datetime


def strauto(clazz):
    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % member for member in vars(self).items())
        )
    clazz.__str__ = __str__
    return clazz


class Requests:

    def getEntityObject(self):
        pass

    def __init__(self, json):
        pass


@strauto
class CreateUserRequests(Requests):

    def getUsername(self):
        return self._username

    def getPassword(self):
        return self._password

    def getEntityObject(self):
        return User(username=self._username, password=hashlib.sha1(self._password.encode()).hexdigest())

    def __init__(self, json):
        if 'username' not in json:
            raise BadRequest('username not passed in the request')
        if 'password' not in json:
            raise BadRequest('password not passed in the request')

        self._username = json['username']
        self._password = json['password']


@strauto
class CreateRideRequests(Requests):

    def getRideId(self):
        return self._rideId

    def getCreatedBy(self):
        return self._created_by

    def getSource(self):
        return self._source

    def getDestination(self):
        return self._destination

    def getTimestamp(self):
        return self._timestamp

    def getEntityObject(self):
        return Ride(created_by=self._created_by, source=self._source, destination=self._destination, timestamp=self._timestamp)

    @staticmethod
    def validateSource(source):
        if source < 1 or source > 198:
            raise BadRequest("invalid source passed")
        return source

    @staticmethod
    def validateDestination(destination):
        if destination < 1 or destination > 198:
            raise BadRequest("invalid destination passed")
        return destination

    @staticmethod
    def validateTimestamp(timestamp):
        try:
            return datetime.strptime(timestamp, "%d-%m-%Y:%S-%M-%H")
        except Exception as ex:
            print(ex)
            raise BadRequest(
                "invalid timestamp %s. Please user the format DD-MM-YYYY:SS-MM-HH" % (timestamp))
        return timestamp

    def __init__(self, json):
        if 'created_by' not in json:
            raise BadRequest('created_by not passed in the request')
        if 'timestamp' not in json:
            raise BadRequest('timestamp not passed in the request')
        if 'source' not in json:
            raise BadRequest('source not passed in the request')
        if 'destination' not in json:
            raise BadRequest('destination not passed in the request')

        self._created_by = json['created_by']
        self._source = CreateRideRequests.validateSource(json['source'])
        self._destination = CreateRideRequests.validateDestination(json['destination'])
        self._timestamp = CreateRideRequests.validateTimestamp(json['timestamp'])
