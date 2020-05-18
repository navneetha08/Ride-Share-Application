import hashlib

from werkzeug.exceptions import BadRequest

#from database_rides import Ride
from datetime import datetime
import re


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

    @staticmethod
    def validateSource(source):
        try:
            source = int(source)
            if source < 1 or source > 198:
                print ("source is %d" % source)
                raise BadRequest("invalid source passed")
            return source
        except:
            raise BadRequest("invalid source passed")

    @staticmethod
    def validateDestination(destination):
        try:
            destination = int(destination)
            if destination < 1 or destination > 198:
                raise BadRequest("invalid destination passed")
            return destination
        except:
            raise BadRequest("invalid destination passed")

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
