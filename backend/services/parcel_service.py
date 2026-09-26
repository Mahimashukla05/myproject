import secrets
import string
import logging
from models.parcel_model import ParcelModel

logger = logging.getLogger("parcel_routing_app")

class ParcelService:
    MAX_TEXT_LENGTH = 100

    @classmethod
    def generate_parcel_id(cls):
        alphabet = string.ascii_uppercase + string.digits
        suffix = ''.join(secrets.choice(alphabet) for _ in range(8))
        return f"PCL-{suffix}"

    @classmethod
    def validate_string_field(cls, value, field_name):
        if not isinstance(value, str) or isinstance(value, bool):
            return f"Field '{field_name}' must be a string."
        clean = value.strip()
        if not clean:
            return f"Field '{field_name}' cannot be empty."
        if len(clean) > cls.MAX_TEXT_LENGTH:
            return f"Field '{field_name}' exceeds maximum allowed length of {cls.MAX_TEXT_LENGTH} characters."
        return None

    @classmethod
    def validate_numeric_field(cls, value, field_name, min_value=0.0, allow_zero=False):
        # Reject booleans because in Python bool is a subclass of int (True == 1)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return f"Field '{field_name}' must be a numeric value."
        val = float(value)
        if allow_zero:
            if val < min_value:
                return f"Field '{field_name}' must be non-negative (>= {min_value})."
        else:
            if val <= min_value:
                return f"Field '{field_name}' must be greater than {min_value}."
        return None

    @classmethod
    def create_parcel(cls, data, user_id):
        if not isinstance(data, dict):
            return {"success": False, "error": "Invalid request payload format. Must be a JSON object."}, 400

        # Disallow client from supplying metadata overrides
        forbidden_client_fields = ["submittedBy", "status", "department", "insuranceRequired", "insuranceStatus", "parcelId"]
        for ff in forbidden_client_fields:
            if ff in data and ff != "submittedBy":
                logger.warning(f"Client attempted to supply controlled metadata field '{ff}'")

        senderName = data.get("senderName")
        senderContact = data.get("senderContact")
        receiverName = data.get("receiverName")
        receiverContact = data.get("receiverContact")
        origin = data.get("origin")
        destination = data.get("destination")
        weightKg = data.get("weightKg")
        valueEur = data.get("valueEur")

        # 1. Required fields presence check
        required_fields = ["senderName", "senderContact", "receiverName", "receiverContact", "origin", "destination", "weightKg", "valueEur"]
        missing = [f for f in required_fields if f not in data or data[f] is None]
        if missing:
            return {"success": False, "error": f"Missing required fields: {', '.join(missing)}"}, 400

        # 2. String fields validation
        for fname, fval in [
            ("senderName", senderName),
            ("senderContact", senderContact),
            ("receiverName", receiverName),
            ("receiverContact", receiverContact),
            ("origin", origin),
            ("destination", destination)
        ]:
            err = cls.validate_string_field(fval, fname)
            if err:
                return {"success": False, "error": err}, 400

        # 3. Numeric fields validation
        err = cls.validate_numeric_field(weightKg, "weightKg", min_value=0.0, allow_zero=False)
        if err:
            return {"success": False, "error": err}, 400

        err = cls.validate_numeric_field(valueEur, "valueEur", min_value=0.0, allow_zero=True)
        if err:
            return {"success": False, "error": err}, 400

        # 4. Generate unique parcel ID
        parcel_id = cls.generate_parcel_id()
        # Guarantee uniqueness in unlikely collision
        attempts = 0
        while ParcelModel.find_by_parcel_id(parcel_id) is not None and attempts < 5:
            parcel_id = cls.generate_parcel_id()
            attempts += 1

        # 5. Persist parcel record
        parcel_doc = ParcelModel.create_parcel({
            "parcelId": parcel_id,
            "senderName": senderName,
            "senderContact": senderContact,
            "receiverName": receiverName,
            "receiverContact": receiverContact,
            "origin": origin,
            "destination": destination,
            "weightKg": weightKg,
            "valueEur": valueEur,
            "submittedBy": user_id
        })

        logger.info(f"Parcel created successfully with ID '{parcel_id}' by user '{user_id}'")
        return {"success": True, "parcel": ParcelModel.to_dict(parcel_doc)}, 201

    @classmethod
    def get_parcel(cls, parcel_id, current_user=None):
        if not isinstance(parcel_id, str) or not parcel_id.strip():
            return {"success": False, "error": "Invalid parcel ID specified."}, 400

        doc = ParcelModel.find_by_parcel_id(parcel_id)
        if not doc:
            return {"success": False, "error": f"Parcel with ID '{parcel_id}' not found."}, 404

        if current_user and isinstance(current_user, dict):
            role = current_user.get("role", "")
            user_id = str(current_user.get("_id") or current_user.get("id"))
            if role not in ["admin", "operator"]:
                return {"success": False, "error": "Access denied."}, 403

        return {"success": True, "parcel": ParcelModel.to_dict(doc)}, 200

    @classmethod
    def get_paginated_parcels(cls, query_filters=None, user_id=None, role='operator', page=1, limit=20, sort_field='-submittedAt'):
        result = ParcelModel.get_paginated_parcels(
            query_filters=query_filters,
            user_id=user_id,
            role=role,
            page=page,
            limit=limit,
            sort_field=sort_field
        )
        if result is None:
            return {
                "success": False,
                "error": "Database is currently unavailable. Please try again later.",
                "errorType": "TECHNICAL"
            }, 503

        return {"success": True, **result}, 200

