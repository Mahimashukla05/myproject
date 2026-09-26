from datetime import datetime, timezone
from bson import ObjectId
from config.db import Database

class AuditModel:
    COLLECTION_NAME = "audit_logs"

    @classmethod
    def get_collection(cls):
        db = Database.get_db()
        if db is not None:
            collection = db[cls.COLLECTION_NAME]
            collection.create_index([("timestamp", -1)])
            return collection
        return None

    @classmethod
    def log_event(cls, actor_id, actor_username, actor_role, action, parcel_id, details=None):
        collection = cls.get_collection()
        now = datetime.now(timezone.utc).isoformat()
        
        doc = {
            "actorId": str(actor_id),
            "actorUsername": str(actor_username),
            "actorRole": str(actor_role),
            "action": str(action),
            "parcelId": str(parcel_id) if parcel_id else None,
            "timestamp": now,
            "details": details or {}
        }

        if collection is not None:
            result = collection.insert_one(doc)
            doc["_id"] = str(result.inserted_id)
            return doc
        else:
            doc["_id"] = str(ObjectId())
            return doc

    @classmethod
    def get_all_logs(cls):
        collection = cls.get_collection()
        if collection is not None:
            logs = list(collection.find({}).sort([("timestamp", -1)]))
            for l in logs:
                l["_id"] = str(l["_id"])
            return logs
        return []

    @classmethod
    def get_paginated_logs(cls, page=1, limit=20, query_filters=None):
        collection = cls.get_collection()
        if collection is None:
            return {
                "logs": [],
                "page": 1,
                "limit": 20,
                "total": 0,
                "totalPages": 1
            }

        try:
            page = int(page)
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1

        try:
            limit = int(limit)
            if limit < 1:
                limit = 20
            elif limit > 100:
                limit = 100
        except (ValueError, TypeError):
            limit = 20

        q = {}
        whitelisted_keys = ["action", "actorUsername", "actorRole", "parcelId", "actorId"]
        if query_filters and isinstance(query_filters, dict):
            for k in whitelisted_keys:
                if k in query_filters and query_filters[k]:
                    val = str(query_filters[k]).strip()
                    if val:
                        q[k] = val

        logs = list(collection.find(q).sort([("timestamp", -1)]))
        total = len(logs)
        total_pages = (total + limit - 1) // limit if total > 0 else 1

        skip = (page - 1) * limit
        paginated_logs = logs[skip:skip + limit]

        for l in paginated_logs:
            l["_id"] = str(l["_id"])

        return {
            "logs": paginated_logs,
            "page": page,
            "limit": limit,
            "total": total,
            "totalPages": total_pages
        }
