import datetime
import pymongo
import uuid
import pytz

class MongoBlog:
    def __init__(self, database, collection, **kwargs):
        self._conn = pymongo.MongoClient(**kwargs)
        self._coll = self._conn[database][collection]

    def get_index(self, user=None):
        if user is None:
            entries = self._coll.find().sort('ts', pymongo.DESCENDING)
        else:
            entries = self._coll.find({"user": user}).sort('ts', pymongo.DESCENDING)
        return entries

    def create_entry(self, title, body, image_filename, audio_filename, user):
        entry_id = uuid.uuid4().hex
        ts = datetime.datetime.now(pytz.timezone('UTC'))
        self._coll.insert({"entry_id": entry_id,
                           "title": title,
                           "body": body,
                           "image": image_filename,
                           "audio": audio_filename,
                           "user": user,
                           "ts": ts,
                           "last_update": ts})
        return

    def delete_entry(self, entry_id):
        self._coll.remove({"entry_id": entry_id})

    def delete_all_entries(self):
        self._coll.remove({})

    def get_entry(self, entry_id):
        return self._coll.find_one({"entry_id": entry_id})

    def update_entry(self, entry_id, title, body, image_filename, audio_filename, user):
        entry = self._coll.find_one({"entry_id": entry_id})
        ts = entry['ts']
        last_update = datetime.datetime.now(pytz.timezone('UTC'))
        self._coll.update({"entry_id": entry_id}, {"entry_id": entry_id,
                                                   "title": title,
                                                   "body": body,
                                                   "image": image_filename,
                                                   "audio": audio_filename,
                                                   "user": user,
                                                   "ts": ts,
                                                   "last_update": last_update})
