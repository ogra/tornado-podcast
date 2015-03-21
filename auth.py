import pymongo
import uuid
import re

from passlib.hash import pbkdf2_sha512

class Authentication:
    def log_in(self, username, password):
        return False

    def log_out(self, username):
        return

    def register(self, username, password, acls):
        return False

    def get_acls(self, username):
        return []

    def has_acl(self, username, acl):
        return False

class MongoAuthentication(Authentication):
    def __init__(self, database, collection, **kwargs):
        self._conn = pymongo.MongoClient(**kwargs)
        self._coll = self._conn[database][collection]

    def log_in(self, username, password):
        record = self._coll.find_one({"username": username})
        if record is None:
            return False
        password_hash = record['password']
        return pbkdf2_sha512.verify(password, password_hash)

    def log_out(self, username):
        return

    def validate_username(self, username):
        if re.match("^[a-zA-Z0-9\-_]+$", username):
            return True
        else:
            return False

    def register(self, username, password, acls=[]):
        if username is None or password is None or username == "" or\
                password == "":
            return False

        if not self.validate_username(username):
            return False

        record = self._coll.find_one({"username": username})
        if record is not None:
            return False

        password_hash = pbkdf2_sha512.encrypt(password, rounds=128000)
        self._coll.insert({"username": username, "password": password_hash, "acl": acls})
        return True

    def get_acls(self, username):
        record = self._coll.find_one({"username": username})
        if record is None:
            return []
        return record['acl']

    def has_acl(self, username, acl):
        acls = self.get_acls(username)
        return acl in acls

    def get_subdir_name(self, username):
        record = self._coll.find_one({"username": username})
        if record is None:
            return False
        if not "subdir" in record or record["subdir"] is None:
            subdir = username + '-' + uuid.uuid4().hex
            self._coll.update({"username": username},
                              {"username": username,
                               "password": record["password"],
                               "acl": record["acl"],
                               "subdir": subdir})
            return subdir
        else:
            return record["subdir"]
