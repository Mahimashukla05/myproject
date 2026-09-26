from datetime import datetime, timezone
from bson import ObjectId
from config.db import Database

class UserModel:
    COLLECTION_NAME = "users"

    @classmethod
    def get_collection(cls):
        db = Database.get_db()
        if db is not None:
            collection = db[cls.COLLECTION_NAME]
            collection.create_index("username", unique=True)
            collection.create_index("email", unique=True)
            collection.create_index("mobile", unique=True)
            return collection
        return None

    @classmethod
    def create_user(cls, user_data):
        collection = cls.get_collection()
        now = datetime.now(timezone.utc).isoformat()
        
        # Enforce string types
        doc = {
            "fullName": str(user_data["fullName"]).strip(),
            "username": str(user_data["username"]).lower().strip(),
            "email": str(user_data["email"]).lower().strip(),
            "mobile": str(user_data["mobile"]).strip(),
            "passwordHash": str(user_data["passwordHash"]),
            "role": str(user_data.get("role", "user")).lower().strip(),
            "createdAt": now,
            "updatedAt": now,
            "isActive": True
        }
        if collection is not None:
            result = collection.insert_one(doc)
            doc["_id"] = str(result.inserted_id)
            return doc
        else:
            doc["_id"] = str(ObjectId())
            return doc

    @classmethod
    def find_by_username(cls, username):
        if not isinstance(username, str):
            return None
        collection = cls.get_collection()
        if collection is not None:
            return collection.find_one({"username": username.lower().strip()})
        return None

    @classmethod
    def find_by_email(cls, email):
        if not isinstance(email, str):
            return None
        collection = cls.get_collection()
        if collection is not None:
            return collection.find_one({"email": email.lower().strip()})
        return None

    @classmethod
    def find_by_mobile(cls, mobile):
        if not isinstance(mobile, str):
            return None
        collection = cls.get_collection()
        if collection is not None:
            return collection.find_one({"mobile": mobile.strip()})
        return None

    @classmethod
    def find_by_identifier(cls, identifier):
        """Sanitize & search by username, email, OR mobile number safely against NoSQL injection."""
        if not isinstance(identifier, str):
            return None
        val = identifier.strip().lower()
        if not val:
            return None
            
        collection = cls.get_collection()
        if collection is not None:
            return collection.find_one({
                "$or": [
                    {"username": val},
                    {"email": val},
                    {"mobile": identifier.strip()}
                ]
            })
        return None

    @classmethod
    def find_by_id(cls, user_id):
        if not isinstance(user_id, str):
            return None
        collection = cls.get_collection()
        if collection is not None:
            try:
                return collection.find_one({"_id": ObjectId(user_id)})
            except Exception:
                return None
        return None

    @classmethod
    def update_password(cls, user_id, new_password_hash):
        if not isinstance(user_id, str) or not isinstance(new_password_hash, str):
            return False
        collection = cls.get_collection()
        if collection is not None:
            now = datetime.now(timezone.utc).isoformat()
            try:
                collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"passwordHash": new_password_hash, "updatedAt": now}}
                )
                return True
            except Exception:
                return False
        return False

    @classmethod
    def get_all_users(cls):
        collection = cls.get_collection()
        if collection is not None:
            users = list(collection.find({}, {"passwordHash": 0}))
            for u in users:
                u["_id"] = str(u["_id"])
            return users
        return []

    @classmethod
    def to_dict(cls, user_doc):
        if not user_doc:
            return None
        return {
            "id": str(user_doc["_id"]),
            "fullName": user_doc.get("fullName"),
            "username": user_doc.get("username"),
            "email": user_doc.get("email"),
            "mobile": user_doc.get("mobile"),
            "role": user_doc.get("role"),
            "createdAt": user_doc.get("createdAt"),
            "isActive": user_doc.get("isActive", True)
        }
