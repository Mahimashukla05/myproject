import logging
from models.parcel_model import ParcelModel
from models.audit_model import AuditModel

logger = logging.getLogger("parcel_routing_app")

class LifecycleService:
    VALID_TRANSITIONS = {
        "RECEIVED": ["ROUTING_EVALUATED"],
        "ROUTING_EVALUATED": ["AWAITING_INSURANCE", "ASSIGNED"],
        "AWAITING_INSURANCE": ["INSURANCE_APPROVED", "INSURANCE_REJECTED"],
        "INSURANCE_APPROVED": ["ASSIGNED"],
        "ASSIGNED": ["IN_PROCESSING"],
        "IN_PROCESSING": ["COMPLETED", "FAILED"]
    }

    @classmethod
    def approve_insurance(cls, parcel_id, actor):
        if not isinstance(parcel_id, str) or not parcel_id.strip():
            return {"success": False, "error": "Invalid parcel ID specified."}, 400

        parcel = ParcelModel.find_by_parcel_id(parcel_id)
        if not parcel:
            return {"success": False, "error": f"Parcel with ID '{parcel_id}' not found."}, 404

        current_status = parcel.get("status")
        ins_req = parcel.get("insuranceRequired", False)
        ins_status = parcel.get("insuranceStatus")

        if not ins_req or ins_status != "PENDING" or current_status != "AWAITING_INSURANCE":
            return {
                "success": False,
                "error": f"Cannot approve insurance. Parcel '{parcel_id}' is in status '{current_status}' with insurance status '{ins_status}'."
            }, 400

        extra = {"insuranceStatus": "APPROVED"}
        updated_doc = ParcelModel.update_parcel_status(parcel_id, "INSURANCE_APPROVED", extra)
        if updated_doc is None:
            updated_doc = dict(parcel)
            updated_doc.update({"status": "INSURANCE_APPROVED", "insuranceStatus": "APPROVED"})

        # Record Audit Event
        actor_id = actor.get("_id") or actor.get("id") or "system"
        AuditModel.log_event(
            actor_id=actor_id,
            actor_username=actor.get("username", "unknown"),
            actor_role=actor.get("role", "admin"),
            action="Insurance Approved",
            parcel_id=parcel_id,
            details={"oldStatus": current_status, "newStatus": "INSURANCE_APPROVED", "oldInsuranceStatus": ins_status, "newInsuranceStatus": "APPROVED"}
        )

        logger.info(f"Admin '{actor.get('username')}' approved insurance for parcel '{parcel_id}'")
        return {"success": True, "parcel": ParcelModel.to_dict(updated_doc)}, 200

    @classmethod
    def reject_insurance(cls, parcel_id, reason, actor):
        if not isinstance(parcel_id, str) or not parcel_id.strip():
            return {"success": False, "error": "Invalid parcel ID specified."}, 400

        if not isinstance(reason, str) or not reason.strip():
            return {"success": False, "error": "Rejection reason is required and cannot be empty."}, 400

        parcel = ParcelModel.find_by_parcel_id(parcel_id)
        if not parcel:
            return {"success": False, "error": f"Parcel with ID '{parcel_id}' not found."}, 404

        current_status = parcel.get("status")
        ins_req = parcel.get("insuranceRequired", False)
        ins_status = parcel.get("insuranceStatus")

        if not ins_req or ins_status != "PENDING" or current_status != "AWAITING_INSURANCE":
            return {
                "success": False,
                "error": f"Cannot reject insurance. Parcel '{parcel_id}' is in status '{current_status}' with insurance status '{ins_status}'."
            }, 400

        clean_reason = reason.strip()
        extra = {"insuranceStatus": "REJECTED", "failureReason": clean_reason}
        updated_doc = ParcelModel.update_parcel_status(parcel_id, "INSURANCE_REJECTED", extra)
        if updated_doc is None:
            updated_doc = dict(parcel)
            updated_doc.update({"status": "INSURANCE_REJECTED", "insuranceStatus": "REJECTED", "failureReason": clean_reason})

        actor_id = actor.get("_id") or actor.get("id") or "system"
        AuditModel.log_event(
            actor_id=actor_id,
            actor_username=actor.get("username", "unknown"),
            actor_role=actor.get("role", "admin"),
            action="Insurance Rejected",
            parcel_id=parcel_id,
            details={"oldStatus": current_status, "newStatus": "INSURANCE_REJECTED", "reason": clean_reason}
        )

        logger.info(f"Admin '{actor.get('username')}' rejected insurance for parcel '{parcel_id}' (Reason: {clean_reason})")
        return {"success": True, "parcel": ParcelModel.to_dict(updated_doc)}, 200

    @classmethod
    def transition_parcel(cls, parcel_id, target_status, action_name, actor):
        if not isinstance(parcel_id, str) or not parcel_id.strip():
            return {"success": False, "error": "Invalid parcel ID specified."}, 400

        parcel = ParcelModel.find_by_parcel_id(parcel_id)
        if not parcel:
            return {"success": False, "error": f"Parcel with ID '{parcel_id}' not found."}, 404

        current_status = parcel.get("status")
        allowed_targets = cls.VALID_TRANSITIONS.get(current_status, [])

        if target_status not in allowed_targets:
            return {
                "success": False,
                "error": f"Invalid parcel status transition from '{current_status}' to '{target_status}'."
            }, 400

        # Special check: Routing evaluated parcel requiring insurance cannot jump directly to ASSIGNED
        if current_status == "ROUTING_EVALUATED" and target_status == "ASSIGNED":
            if parcel.get("insuranceRequired", False):
                return {
                    "success": False,
                    "error": "Parcel requires insurance approval before it can be assigned."
                }, 400

        updated_doc = ParcelModel.update_parcel_status(parcel_id, target_status)
        if updated_doc is None:
            updated_doc = dict(parcel)
            updated_doc["status"] = target_status

        actor_id = actor.get("_id") or actor.get("id") or "system"
        AuditModel.log_event(
            actor_id=actor_id,
            actor_username=actor.get("username", "unknown"),
            actor_role=actor.get("role", "user"),
            action=action_name,
            parcel_id=parcel_id,
            details={"oldStatus": current_status, "newStatus": target_status}
        )

        logger.info(f"User '{actor.get('username')}' transitioned parcel '{parcel_id}' from '{current_status}' to '{target_status}' ({action_name})")
        return {"success": True, "parcel": ParcelModel.to_dict(updated_doc)}, 200
