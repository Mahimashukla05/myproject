from datetime import datetime, timezone
from bson import ObjectId
from config.db import Database

class RoutingRuleModel:
    COLLECTION_NAME = "routing_rules"

    @classmethod
    def get_collection(cls):
        db = Database.get_db()
        if db is not None:
            collection = db[cls.COLLECTION_NAME]
            collection.create_index("version", unique=True)
            return collection
        return None

    @classmethod
    def get_default_rule_data(cls):
        return {
            "version": 1,
            "isActive": True,
            "departmentRules": [
                { "department": "MAIL", "minWeight": 0.0, "minOp": "GT", "maxWeight": 1.0, "maxOp": "LTE" },
                { "department": "REGULAR", "minWeight": 1.0, "minOp": "GT", "maxWeight": 10.0, "maxOp": "LTE" },
                { "department": "HEAVY", "minWeight": 10.0, "minOp": "GT", "maxWeight": None, "maxOp": None }
            ],
            "insuranceRule": {
                "thresholdEur": 1000.0,
                "operator": "GT"
            },
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "createdBy": "system",
            "activatedAt": datetime.now(timezone.utc).isoformat(),
            "activatedBy": "system"
        }

    @classmethod
    def seed_default_rules(cls):
        collection = cls.get_collection()
        if collection is not None:
            active_doc = collection.find_one({"isActive": True})
            if not active_doc:
                # Check if version 1 exists
                v1 = collection.find_one({"version": 1})
                if not v1:
                    default_data = cls.get_default_rule_data()
                    res = collection.insert_one(default_data)
                    default_data["_id"] = str(res.inserted_id)
                    return default_data
                else:
                    v1["_id"] = str(v1["_id"])
                    return v1
            active_doc["_id"] = str(active_doc["_id"])
            return active_doc
        default_data = cls.get_default_rule_data()
        default_data["_id"] = str(ObjectId())
        return default_data

    @classmethod
    def get_active_rules(cls):
        collection = cls.get_collection()
        if collection is not None:
            doc = collection.find_one({"isActive": True})
            if not doc:
                return cls.seed_default_rules()
            doc["_id"] = str(doc["_id"])
            return doc
        res = cls.get_default_rule_data()
        res["_id"] = str(ObjectId())
        return res

    @classmethod
    def get_rule_history(cls):
        collection = cls.get_collection()
        if collection is not None:
            docs = list(collection.find({}).sort("version", -1))
            if not docs:
                cls.seed_default_rules()
                docs = list(collection.find({}).sort("version", -1))
            for d in docs:
                d["_id"] = str(d["_id"])
            return docs
        res = cls.get_default_rule_data()
        res["_id"] = str(ObjectId())
        return [res]

    @classmethod
    def get_rule_by_version(cls, version):
        collection = cls.get_collection()
        if collection is not None:
            doc = collection.find_one({"version": int(version)})
            if doc:
                doc["_id"] = str(doc["_id"])
            return doc
        return None

    @classmethod
    def create_and_activate_version(cls, department_rules, insurance_rule, user_id, username):
        collection = cls.get_collection()
        now = datetime.now(timezone.utc).isoformat()

        if collection is not None:
            # Determine next version number
            existing = list(collection.find({}))
            max_v = max([d.get("version", 1) for d in existing]) if existing else 0
            new_version = max_v + 1

            # Deactivate currently active version
            collection.update_many(
                {"isActive": True},
                {"$set": {"isActive": False, "deactivatedAt": now, "deactivatedBy": str(username)}}
            )

            new_doc = {
                "version": new_version,
                "isActive": True,
                "departmentRules": department_rules,
                "insuranceRule": insurance_rule,
                "createdAt": now,
                "createdBy": str(username),
                "activatedAt": now,
                "activatedBy": str(username)
            }

            result = collection.insert_one(new_doc)
            new_doc["_id"] = str(result.inserted_id)
            return new_doc
        else:
            new_doc = {
                "_id": str(ObjectId()),
                "version": 2,
                "isActive": True,
                "departmentRules": department_rules,
                "insuranceRule": insurance_rule,
                "createdAt": now,
                "createdBy": str(username),
                "activatedAt": now,
                "activatedBy": str(username)
            }
            return new_doc
