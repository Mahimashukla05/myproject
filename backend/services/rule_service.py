import logging
from models.routing_rule_model import RoutingRuleModel
from models.rule_change_request_model import RuleChangeRequestModel
from models.audit_model import AuditModel

logger = logging.getLogger("parcel_routing_app")

class RuleService:
    ALLOWED_ACTIONS = {"ADD", "MODIFY", "DEACTIVATE"}
    ALLOWED_CATEGORIES = {"DEPARTMENT", "INSURANCE"}
    ALLOWED_DEPARTMENTS = {"MAIL", "REGULAR", "HEAVY"}

    @classmethod
    def validate_rule_set(cls, department_rules, insurance_rule):
        if not isinstance(department_rules, list) or len(department_rules) == 0:
            return False, "Department rules list must not be empty."

        # Check required department names
        depts_found = {r.get("department") for r in department_rules if isinstance(r, dict)}
        if not cls.ALLOWED_DEPARTMENTS.issubset(depts_found):
            missing = cls.ALLOWED_DEPARTMENTS - depts_found
            return False, f"Missing required department rules for: {', '.join(missing)}"

        # Validate operators and numerical values
        for r in department_rules:
            dept = r.get("department")
            if dept not in cls.ALLOWED_DEPARTMENTS:
                return False, f"Unsupported department name '{dept}'."

            min_w = r.get("minWeight")
            min_op = r.get("minOp")
            max_w = r.get("maxWeight")
            max_op = r.get("maxOp")

            if min_w is not None:
                if not isinstance(min_w, (int, float)) or min_w < 0:
                    return False, f"Invalid minWeight for department {dept}."
                if min_op not in ["GT", "GTE"]:
                    return False, f"Invalid minOp '{min_op}' for department {dept}."

            if max_w is not None:
                if not isinstance(max_w, (int, float)) or max_w <= 0:
                    return False, f"Invalid maxWeight for department {dept}."
                if max_op not in ["LT", "LTE"]:
                    return False, f"Invalid maxOp '{max_op}' for department {dept}."

            if min_w is not None and max_w is not None and min_w >= max_w:
                return False, f"Min weight ({min_w}) must be less than max weight ({max_w}) for department {dept}."

        # Check gaps or overlaps in weight coverage
        sorted_rules = sorted(department_rules, key=lambda x: x.get("minWeight") or 0.0)
        # Mail (0.0 to X), Regular (X to Y), Heavy (Y to None)
        mail_rule = next((r for r in sorted_rules if r.get("department") == "MAIL"), None)
        reg_rule = next((r for r in sorted_rules if r.get("department") == "REGULAR"), None)
        heavy_rule = next((r for r in sorted_rules if r.get("department") == "HEAVY"), None)

        if not mail_rule or not reg_rule or not heavy_rule:
            return False, "Department rules must include MAIL, REGULAR, and HEAVY coverage."

        mail_max = mail_rule.get("maxWeight")
        reg_min = reg_rule.get("minWeight")
        reg_max = reg_rule.get("maxWeight")
        heavy_min = heavy_rule.get("minWeight")

        if mail_max != reg_min:
            return False, f"Boundary gap/overlap between MAIL maxWeight ({mail_max}) and REGULAR minWeight ({reg_min})."
        if reg_max != heavy_min:
            return False, f"Boundary gap/overlap between REGULAR maxWeight ({reg_max}) and HEAVY minWeight ({heavy_min})."

        # Validate insurance rule
        if not isinstance(insurance_rule, dict):
            return False, "Insurance rule configuration must be an object."

        t_eur = insurance_rule.get("thresholdEur")
        op = insurance_rule.get("operator")

        if t_eur is None or not isinstance(t_eur, (int, float)) or t_eur < 0:
            return False, "Insurance thresholdEur must be a non-negative number."

        if op not in ["GT", "GTE"]:
            return False, f"Unsupported insurance operator '{op}'."

        return True, None

    @classmethod
    def get_active_rule_set(cls):
        return RoutingRuleModel.get_active_rules()

    @classmethod
    def get_rule_history(cls):
        return RoutingRuleModel.get_rule_history()

    @classmethod
    def create_change_request(cls, data, current_user):
        if not isinstance(data, dict):
            return {"success": False, "error": "Invalid request payload format."}, 400

        action = str(data.get("action", "")).upper()
        category = str(data.get("category", "")).upper()
        reason = str(data.get("reason", "")).strip()

        if action not in cls.ALLOWED_ACTIONS:
            return {"success": False, "error": f"Invalid action '{action}'. Supported: ADD, MODIFY, DEACTIVATE."}, 400

        if category not in cls.ALLOWED_CATEGORIES:
            return {"success": False, "error": f"Invalid category '{category}'. Supported: DEPARTMENT, INSURANCE."}, 400

        if not reason or len(reason) < 3:
            return {"success": False, "error": "A clear reason (at least 3 characters) is required for rule change request."}, 400

        user_id = str(current_user.get("_id") or current_user.get("id"))
        username = current_user.get("username", "operator")
        role = current_user.get("role", "operator")

        req_doc = RuleChangeRequestModel.create_request(data, user_id, username)

        AuditModel.log_event(
            actor_id=user_id,
            actor_username=username,
            actor_role=role,
            action="RULE_CHANGE_REQUEST_CREATED",
            parcel_id=None,
            details={"requestId": req_doc["requestId"], "action": action, "category": category, "reason": reason}
        )

        logger.info(f"Operator '{username}' created rule change request '{req_doc['requestId']}' ({action} {category})")
        return {"success": True, "request": req_doc}, 201

    @classmethod
    def get_change_requests(cls, query_filters, current_user):
        role = current_user.get("role", "user")
        user_id = str(current_user.get("_id") or current_user.get("id"))

        if role == "user":
            return {"success": False, "error": "Access denied."}, 403

        filters = {}
        if query_filters and isinstance(query_filters, dict):
            if "status" in query_filters and query_filters["status"]:
                filters["status"] = query_filters["status"]

        if role == "operator":
            filters["requestedBy"] = user_id

        requests = RuleChangeRequestModel.get_requests(filters)
        return {"success": True, "requests": requests}, 200

    @classmethod
    def get_change_request_by_id(cls, request_id, current_user):
        role = current_user.get("role", "user")
        user_id = str(current_user.get("_id") or current_user.get("id"))

        if role == "user":
            return {"success": False, "error": "Access denied."}, 403

        req = RuleChangeRequestModel.find_by_request_id(request_id)
        if not req:
            return {"success": False, "error": f"Rule change request '{request_id}' not found."}, 404

        if role == "operator" and str(req.get("requestedBy")) != user_id:
            return {"success": False, "error": "Access denied. You can only view your own requests."}, 403

        return {"success": True, "request": req}, 200

    @classmethod
    def approve_change_request(cls, request_id, current_user, confirm=False):
        role = current_user.get("role", "user")
        user_id = str(current_user.get("_id") or current_user.get("id"))
        username = current_user.get("username", "admin")

        if role != "admin":
            return {"success": False, "error": "Access denied. Admin role required."}, 403

        if not confirm:
            return {"success": False, "error": "Explicit confirmation parameter 'confirm: true' is required to activate a new rule version."}, 400

        req = RuleChangeRequestModel.find_by_request_id(request_id)
        if not req:
            return {"success": False, "error": f"Rule change request '{request_id}' not found."}, 404

        if req.get("status") != "PENDING":
            return {"success": False, "error": f"Cannot approve request with status '{req.get('status')}'. Only PENDING requests can be approved."}, 400

        # Load active rules and construct proposed new configuration
        active_set = cls.get_active_rule_set()
        dept_rules = list(active_set.get("departmentRules", []))
        ins_rule = dict(active_set.get("insuranceRule", {}))

        category = req.get("category")
        action = str(req.get("action", "MODIFY")).upper()
        proposed = req.get("proposedChange") or {}

        if category == "DEPARTMENT":
            target_dept = req.get("targetDepartment") or proposed.get("department")
            new_dept_list = []
            updated = False
            for r in dept_rules:
                r_copy = dict(r)
                if r_copy.get("department") == target_dept:
                    if action == "DEACTIVATE":
                        updated = True
                        continue
                    else:
                        r_copy.update(proposed)
                        updated = True
                new_dept_list.append(r_copy)
            if not updated and target_dept and action != "DEACTIVATE":
                new_dept_list.append(proposed)
            dept_rules = new_dept_list
        elif category == "INSURANCE":
            if action == "DEACTIVATE":
                ins_rule = {"thresholdEur": 999999999.0, "operator": "GT"}
            else:
                ins_rule.update(proposed)

        # Validate the resulting complete rule configuration
        is_valid, err = cls.validate_rule_set(dept_rules, ins_rule)
        if not is_valid:
            logger.warning(f"Admin approval failed for request '{request_id}': resulting rule set invalid ({err})")
            return {"success": False, "error": f"Invalid resulting rule set: {err}"}, 400

        # Activate new rule version
        new_version_doc = RoutingRuleModel.create_and_activate_version(dept_rules, ins_rule, user_id, username)

        # Update request status to APPROVED
        updated_req = RuleChangeRequestModel.update_request_status(request_id, "APPROVED", user_id, username)

        # Log audit events
        AuditModel.log_event(
            actor_id=user_id, actor_username=username, actor_role=role,
            action="RULE_CHANGE_APPROVED", parcel_id=None,
            details={"requestId": request_id, "newVersion": new_version_doc["version"]}
        )

        AuditModel.log_event(
            actor_id=user_id, actor_username=username, actor_role=role,
            action="RULE_VERSION_ACTIVATED", parcel_id=None,
            details={"version": new_version_doc["version"]}
        )

        logger.info(f"Admin '{username}' approved request '{request_id}' and activated rule version {new_version_doc['version']}")
        return {"success": True, "request": updated_req, "activeRuleVersion": new_version_doc}, 200

    @classmethod
    def reject_change_request(cls, request_id, rejection_reason, current_user):
        role = current_user.get("role", "user")
        user_id = str(current_user.get("_id") or current_user.get("id"))
        username = current_user.get("username", "admin")

        if role != "admin":
            return {"success": False, "error": "Access denied. Admin role required."}, 403

        reason_clean = str(rejection_reason or "").strip()
        if not reason_clean:
            return {"success": False, "error": "Rejection reason is required."}, 400

        req = RuleChangeRequestModel.find_by_request_id(request_id)
        if not req:
            return {"success": False, "error": f"Rule change request '{request_id}' not found."}, 404

        if req.get("status") != "PENDING":
            return {"success": False, "error": f"Cannot reject request with status '{req.get('status')}'. Only PENDING requests can be rejected."}, 400

        updated_req = RuleChangeRequestModel.update_request_status(request_id, "REJECTED", user_id, username, rejection_reason=reason_clean)

        AuditModel.log_event(
            actor_id=user_id, actor_username=username, actor_role=role,
            action="RULE_CHANGE_REJECTED", parcel_id=None,
            details={"requestId": request_id, "rejectionReason": reason_clean}
        )

        logger.info(f"Admin '{username}' rejected rule change request '{request_id}' with reason: {reason_clean}")
        return {"success": True, "request": updated_req}, 200

    @classmethod
    def withdraw_change_request(cls, request_id, current_user):
        role = current_user.get("role", "user")
        user_id = str(current_user.get("_id") or current_user.get("id"))
        username = current_user.get("username", "operator")

        req = RuleChangeRequestModel.find_by_request_id(request_id)
        if not req:
            return {"success": False, "error": f"Rule change request '{request_id}' not found."}, 404

        # User scoping: Operator can ONLY withdraw their OWN request
        if str(req.get("requestedBy")) != user_id:
            return {"success": False, "error": "Access denied. You can only withdraw your own requests."}, 403

        if req.get("status") != "PENDING":
            return {"success": False, "error": f"Cannot withdraw request with status '{req.get('status')}'. Only PENDING requests can be withdrawn."}, 400

        updated_req = RuleChangeRequestModel.update_request_status(request_id, "WITHDRAWN", user_id, username)

        AuditModel.log_event(
            actor_id=user_id, actor_username=username, actor_role=role,
            action="RULE_CHANGE_WITHDRAWN", parcel_id=None,
            details={"requestId": request_id}
        )

        logger.info(f"Operator '{username}' withdrew rule change request '{request_id}'")
        return {"success": True, "request": updated_req}, 200
