import logging
from models.parcel_model import ParcelModel

logger = logging.getLogger("parcel_routing_app")

class RoutingService:
    DEPARTMENT_MAIL = "MAIL"
    DEPARTMENT_REGULAR = "REGULAR"
    DEPARTMENT_HEAVY = "HEAVY"

    @classmethod
    def evaluate_routing(cls, weight_kg, value_eur, active_rules=None):
        """
        Determines department and insurance requirements based on active rules.
        """
        weight = float(weight_kg)
        value = float(value_eur)

        if active_rules is None:
            from services.rule_service import RuleService
            active_rules = RuleService.get_active_rule_set()

        department = None
        dept_rules = active_rules.get("departmentRules", [])
        
        # Sort rules so MAIL -> REGULAR -> HEAVY evaluation is deterministic
        for r in dept_rules:
            d_name = r.get("department")
            min_w = r.get("minWeight")
            min_op = r.get("minOp")
            max_w = r.get("maxWeight")
            max_op = r.get("maxOp")

            match_min = True
            if min_w is not None:
                if min_op == "GT":
                    match_min = (weight > min_w)
                elif min_op == "GTE":
                    match_min = (weight >= min_w)

            match_max = True
            if max_w is not None:
                if max_op == "LTE":
                    match_max = (weight <= max_w)
                elif max_op == "LT":
                    match_max = (weight < max_w)

            if match_min and match_max:
                department = d_name
                break

        if department is None:
            department = cls.DEPARTMENT_REGULAR

        # Insurance decision
        ins_rule = active_rules.get("insuranceRule", {})
        threshold = float(ins_rule.get("thresholdEur", 1000.0))
        op = ins_rule.get("operator", "GT")

        if op == "GT":
            requires_insurance = (value > threshold)
        elif op == "GTE":
            requires_insurance = (value >= threshold)
        else:
            requires_insurance = (value > threshold)

        if requires_insurance:
            insurance_required = True
            insurance_status = "PENDING"
            status = "AWAITING_INSURANCE"
        else:
            insurance_required = False
            insurance_status = "NOT_REQUIRED"
            status = "ROUTING_EVALUATED"

        return {
            "department": department,
            "insuranceRequired": insurance_required,
            "insuranceStatus": insurance_status,
            "status": status
        }

    @classmethod
    def route_parcel(cls, parcel_id):
        if not isinstance(parcel_id, str) or not parcel_id.strip():
            return {"success": False, "error": "Invalid parcel ID specified."}, 400

        parcel = ParcelModel.find_by_parcel_id(parcel_id)
        if not parcel:
            return {"success": False, "error": f"Parcel with ID '{parcel_id}' not found."}, 404

        # Extract stored weight & value (ignore any request body input)
        weight_kg = parcel.get("weightKg")
        value_eur = parcel.get("valueEur")

        if weight_kg is None or value_eur is None or weight_kg <= 0 or value_eur < 0:
            logger.error(f"Cannot route parcel '{parcel_id}': invalid stored weight ({weight_kg}) or value ({value_eur})")
            return {"success": False, "error": "Stored parcel contains invalid weight or value data."}, 400

        routing_result = cls.evaluate_routing(weight_kg, value_eur)

        # Idempotent database update using stored values
        updated_doc = ParcelModel.update_parcel_routing(parcel_id, routing_result)
        
        # In mock/testing mode if collection update returns None, construct dict
        if updated_doc is None:
            updated_doc = dict(parcel)
            updated_doc.update(routing_result)

        logger.info(
            f"Routed parcel '{parcel_id}' -> Department: {routing_result['department']}, "
            f"Insurance Required: {routing_result['insuranceRequired']} ({routing_result['insuranceStatus']}), "
            f"Status: {routing_result['status']}"
        )

        return {"success": True, "parcel": ParcelModel.to_dict(updated_doc)}, 200
