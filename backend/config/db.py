import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config.settings import Config

logger = logging.getLogger("parcel_routing_app")

class Database:
    _client = None
    _db = None

    @classmethod
    def get_db(cls):
        if cls._db is None:
            cls.connect()
        return cls._db

    @classmethod
    def connect(cls, uri=None):
        mongo_uri = uri or Config.MONGO_URI
        try:
            cls._client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
            cls._client.admin.command('ping')
            db_name = mongo_uri.rstrip('/').split('/')[-1].split('?')[0] or 'parcel_routing_db'
            cls._db = cls._client[db_name]
            logger.info(f"Connected to MongoDB database: {db_name}")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"MongoDB connection failed: {e}. Database is currently unavailable.")
            cls._client = None
            cls._db = None
        return cls._db

    @classmethod
    def is_connected(cls):
        if cls._db is None or cls._client is None:
            return False
        try:
            cls._client.admin.command('ping')
            return True
        except Exception:
            cls._db = None
            cls._client = None
            return False

    @classmethod
    def close(cls):
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._db = None
            logger.info("MongoDB connection closed.")
