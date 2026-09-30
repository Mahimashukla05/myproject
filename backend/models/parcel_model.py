from datetime import datetime, timezone, timedelta
from bson import ObjectId
from config.db import Database

class ParcelModel:
    COLLECTION_NAME = "parcels"

    @classmethod
    def get_collection(cls):
        db = Database.get_db()
        if db is not None:
            collection = db[cls.COLLECTION_NAME]
            collection.create_index("parcelId", unique=True)
            return collection
        return None

    @classmethod
    def create_parcel(cls, parcel_data):
        collection = cls.get_collection()
        now = datetime.now(timezone.utc).isoformat()
        
        doc = {
            "parcelId": str(parcel_data["parcelId"]),
            "senderName": str(parcel_data["senderName"]).strip() if parcel_data.get("senderName") is not None else None,
            "senderContact": str(parcel_data["senderContact"]).strip() if parcel_data.get("senderContact") is not None else None,
            "receiverName": str(parcel_data["receiverName"]).strip() if parcel_data.get("receiverName") is not None else None,
            "receiverContact": str(parcel_data["receiverContact"]).strip() if parcel_data.get("receiverContact") is not None else None,
            "origin": str(parcel_data["origin"]).strip() if parcel_data.get("origin") is not None else None,
            "destination": str(parcel_data["destination"]).strip() if parcel_data.get("destination") is not None else None,
            "weightKg": float(parcel_data["weightKg"]),
            "valueEur": float(parcel_data["valueEur"]),
            "department": None,
            "insuranceRequired": False,
            "insuranceStatus": "NOT_REQUIRED",
            "status": "RECEIVED",
            "submittedBy": str(parcel_data["submittedBy"]),
            "submittedAt": now,
            "updatedAt": now,
            "failureReason": None
        }

        if collection is not None:
            result = collection.insert_one(doc)
            doc["_id"] = str(result.inserted_id)
            return doc
        else:
            doc["_id"] = str(ObjectId())
            return doc

    @classmethod
    def create_failed_parcel(cls, parcel_id_str, item_clean, failure_reason, user_id):
        collection = cls.get_collection()
        now = datetime.now(timezone.utc).isoformat()
        
        target_pid = parcel_id_str
        if cls.find_by_parcel_id(target_pid) is not None:
            unique_suffix = datetime.now(timezone.utc).strftime("%H%M%S%f")[:6]
            target_pid = f"{parcel_id_str}-FAIL-{unique_suffix}"

        doc = {
            "parcelId": target_pid,
            "senderName": str(item_clean.get("senderName")).strip() if item_clean.get("senderName") is not None else "N/A",
            "senderContact": str(item_clean.get("senderContact")).strip() if item_clean.get("senderContact") is not None else "N/A",
            "receiverName": str(item_clean.get("receiverName") or item_clean.get("recipientName")).strip() if (item_clean.get("receiverName") or item_clean.get("recipientName")) is not None else "N/A",
            "receiverContact": str(item_clean.get("receiverContact")).strip() if item_clean.get("receiverContact") is not None else "N/A",
            "origin": str(item_clean.get("origin")).strip() if item_clean.get("origin") is not None else "N/A",
            "destination": str(item_clean.get("destination")).strip() if item_clean.get("destination") is not None else "N/A",
            "weightKg": float(item_clean["weightKg"]) if isinstance(item_clean.get("weightKg"), (int, float)) else 0.0,
            "valueEur": float(item_clean["valueEur"]) if isinstance(item_clean.get("valueEur"), (int, float)) else 0.0,
            "department": None,
            "insuranceRequired": False,
            "insuranceStatus": "NOT_REQUIRED",
            "status": "FAILED",
            "submittedBy": str(user_id),
            "submittedAt": now,
            "updatedAt": now,
            "failureReason": failure_reason
        }

        if collection is not None:
            try:
                result = collection.insert_one(doc)
                doc["_id"] = str(result.inserted_id)
            except Exception:
                pass
        return doc

    @classmethod
    def find_by_parcel_id(cls, parcel_id):
        if not isinstance(parcel_id, str):
            return None
        collection = cls.get_collection()
        if collection is not None:
            doc = collection.find_one({"parcelId": parcel_id.strip()})
            if doc:
                doc["_id"] = str(doc["_id"])
            return doc
        return None

    @classmethod
    def update_parcel_routing(cls, parcel_id, routing_data):
        if not isinstance(parcel_id, str):
            return None
        collection = cls.get_collection()
        now = datetime.now(timezone.utc).isoformat()

        update_fields = {
            "department": routing_data["department"],
            "insuranceRequired": routing_data["insuranceRequired"],
            "insuranceStatus": routing_data["insuranceStatus"],
            "status": routing_data["status"],
            "updatedAt": now
        }

        if collection is not None:
            collection.update_one(
                {"parcelId": parcel_id.strip()},
                {"$set": update_fields}
            )
            return cls.find_by_parcel_id(parcel_id)
        else:
            return None

    @classmethod
    def update_parcel_status(cls, parcel_id, new_status, extra_fields=None):
        if not isinstance(parcel_id, str):
            return None
        collection = cls.get_collection()
        now = datetime.now(timezone.utc).isoformat()

        update_fields = {
            "status": new_status,
            "updatedAt": now
        }
        if extra_fields and isinstance(extra_fields, dict):
            update_fields.update(extra_fields)

        if collection is not None:
            collection.update_one(
                {"parcelId": parcel_id.strip()},
                {"$set": update_fields}
            )
            return cls.find_by_parcel_id(parcel_id)
        else:
            return None

    @classmethod
    def get_parcels(cls, query_filters=None):
        collection = cls.get_collection()
        if collection is not None:
            q = {}
            if query_filters and isinstance(query_filters, dict):
                if "insuranceStatus" in query_filters:
                    q["insuranceStatus"] = str(query_filters["insuranceStatus"])
                if "status" in query_filters:
                    q["status"] = str(query_filters["status"])
                if "submittedBy" in query_filters:
                    q["submittedBy"] = str(query_filters["submittedBy"])
            parcels = list(collection.find(q).sort("submittedAt", -1))
            for p in parcels:
                p["_id"] = str(p["_id"])
            return parcels
        return []

    @classmethod
    def get_dashboard_summary(cls, period="all"):
        collection = cls.get_collection()
        if collection is None:
            return None

        now = datetime.now(timezone.utc)
        match_filter = {}

        if period == "today":
            start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            match_filter["submittedAt"] = {"$gte": start_of_today}
        elif period == "week":
            # Current calendar week: Monday 00:00:00 UTC
            start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            match_filter["submittedAt"] = {"$gte": start_of_week}

        docs = list(collection.find(match_filter))

        totalParcels = len(docs)
        successfullyProcessed = sum(1 for d in docs if d.get("status") in ["COMPLETED", "ROUTING_EVALUATED", "INSURANCE_APPROVED", "ASSIGNED", "IN_PROCESSING"])
        failed = sum(1 for d in docs if d.get("status") in ["FAILED", "INSURANCE_REJECTED"])
        insurancePending = sum(1 for d in docs if d.get("insuranceStatus") == "PENDING")
        insuranceRejected = sum(1 for d in docs if d.get("insuranceStatus") == "REJECTED")

        departmentDistribution = {
            "mail": sum(1 for d in docs if d.get("department") == "MAIL"),
            "regular": sum(1 for d in docs if d.get("department") == "REGULAR"),
            "heavy": sum(1 for d in docs if d.get("department") == "HEAVY")
        }

        return {
            "period": period,
            "totalParcels": totalParcels,
            "successfullyProcessed": successfullyProcessed,
            "failed": failed,
            "insurancePending": insurancePending,
            "insuranceRejected": insuranceRejected,
            "departmentDistribution": departmentDistribution
        }

    @classmethod
    def get_paginated_parcels(cls, query_filters=None, user_id=None, role='admin', page=1, limit=20, sort_field='-submittedAt'):
        collection = cls.get_collection()
        if collection is None:
            return None

        # Sanitize page & limit
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
        # Role-based scoping: only Admin and Operator are valid roles
        if role not in ['admin', 'operator']:
            return {"items": [], "page": 1, "limit": limit, "total": 0, "totalPages": 1}

        if query_filters and isinstance(query_filters, dict):
            if "status" in query_filters and query_filters["status"]:
                q["status"] = str(query_filters["status"])
            if "department" in query_filters and query_filters["department"]:
                q["department"] = str(query_filters["department"])
            if "insuranceStatus" in query_filters and query_filters["insuranceStatus"]:
                q["insuranceStatus"] = str(query_filters["insuranceStatus"])
            if "parcelId" in query_filters and query_filters["parcelId"]:
                pid_clean = str(query_filters["parcelId"]).strip()
                if pid_clean:
                    q["parcelId"] = pid_clean

        # Sorting whitelist
        allowed_sort_fields = {
            "submittedAt": ("submittedAt", 1),
            "-submittedAt": ("submittedAt", -1),
            "parcelId": ("parcelId", 1),
            "-parcelId": ("parcelId", -1),
            "weightKg": ("weightKg", 1),
            "-weightKg": ("weightKg", -1),
            "valueEur": ("valueEur", 1),
            "-valueEur": ("valueEur", -1),
            "status": ("status", 1),
            "-status": ("status", -1),
        }

        sort_key, sort_dir = allowed_sort_fields.get(str(sort_field), ("submittedAt", -1))

        # Query all matching docs
        all_matching = list(collection.find(q).sort([(sort_key, sort_dir)]))
        total_count = len(all_matching)
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

        skip = (page - 1) * limit
        paginated_docs = all_matching[skip:skip + limit]

        for p in paginated_docs:
            p["_id"] = str(p["_id"])

        return {
            "items": paginated_docs,
            "page": page,
            "limit": limit,
            "total": total_count,
            "totalPages": total_pages
        }

    @classmethod
    def to_dict(cls, parcel_doc):
        if not parcel_doc:
            return None
        d = dict(parcel_doc)
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
        return d
