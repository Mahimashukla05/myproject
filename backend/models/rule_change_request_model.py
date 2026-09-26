import secrets
import string
from datetime import datetime, timezone
from bson import ObjectId
from config.db import Database

class RuleChangeRequestModel:
    COLLECTION_NAME = "rule_change_requests"

    @classmethod
    def get_collection(cls):
        db = Database.get_db()
        if db is not None:
            collection = db[cls.COLLECTION_NAME]
            collection.create_index("requestId", unique=True)
            return collection
        return None

    @classmethod
    def generate_request_id(cls):
        alphabet = string.ascii_uppercase + string.digits
        suffix = ''.join(secrets.choice(alphabet) for _ in range(6))
        return f"RCR-{suffix}"

    @classmethod
    def create_request(cls, data, user_id, username):
        collection = cls.get_collection()
        now = datetime.now(timezone.utc).isoformat()
        request_id = cls.generate_request_id()

        doc = {
            "requestId": request_id,
            "action": str(data["action"]).upper(),
            "category": str(data["category"]).upper(),
            "targetDepartment": data.get("targetDepartment"),
            "proposedChange": data.get("proposedChange") or {},
            "reason": str(data["reason"]).strip(),
            "status": "PENDING",
            "requestedBy": str(user_id),
            "requestedByUsername": str(username),
            "createdAt": now,
            "reviewedBy": None,
            "reviewedByUsername": None,
            "reviewedAt": None,
            "rejectionReason": None
        }

        if collection is not None:
            result = collection.insert_one(doc)
            doc["_id"] = str(result.inserted_id)
            return doc
        else:
            doc["_id"] = str(ObjectId())
            return doc

    @classmethod
    def find_by_request_id(cls, request_id):
        if not isinstance(request_id, str):
            return None
        collection = cls.get_collection()
        if collection is not None:
            doc = collection.find_one({"requestId": request_id.strip()})
            if doc:
                doc["_id"] = str(doc["_id"])
            return doc
        return None

    @classmethod
    def get_requests(cls, query_filters=None):
        collection = cls.get_collection()
        if collection is not None:
            q = {}
            if query_filters and isinstance(query_filters, dict):
                if "status" in query_filters and query_filters["status"]:
                    q["status"] = str(query_filters["status"])
                if "requestedBy" in query_filters and query_filters["requestedBy"]:
                    q["requestedBy"] = str(query_filters["requestedBy"])
            requests = list(collection.find(q).sort("createdAt", -1))
            for r in requests:
                r["_id"] = str(r["_id"])
            return requests
        return []

    @classmethod
    def update_request_status(cls, request_id, new_status, user_id, username, rejection_reason=None):
        collection = cls.get_collection()
        now = datetime.now(timezone.utc).isoformat()

        update_fields = {
            "status": new_status,
            "reviewedBy": str(user_id),
            "reviewedByUsername": str(username),
            "reviewedAt": now
        }
        if rejection_reason:
            update_fields["rejectionReason"] = str(rejection_reason).strip()

        if collection is not None:
            collection.update_one(
                {"requestId": request_id.strip()},
                {"$set": update_fields}
            )
            return cls.find_by_request_id(request_id)
        else:
            return None
