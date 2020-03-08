import hashlib

from werkzeug.exceptions import BadRequest
from database_users import User

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
class CreateUserRequests(Requests):

    def getUsername(self):
        return self._username

    def getPassword(self):
        return self._password

    @staticmethod
    def validatePassword(password):
        sha1_re = re.compile("^[a-fA-F0-9]{40}$")

        if sha1_re.search(password) is None:
            raise BadRequest("password is not in sha1 format")

        return password

    def getEntityObject(self):
        return User(username=self._username, password=hashlib.sha1(self._password.encode()).hexdigest())

    def __init__(self, json):
        if 'username' not in json:
            raise BadRequest('username not passed in the request')
        if 'password' not in json:
            raise BadRequest('password not passed in the request')

        self._username = json['username']
        self._password = CreateUserRequests.validatePassword(json['password'])


