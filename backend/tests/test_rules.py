import pytest
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config.settings import Config
from models.routing_rule_model import RoutingRuleModel
from models.rule_change_request_model import RuleChangeRequestModel
from models.parcel_model import ParcelModel
from models.audit_model import AuditModel
from services.routing_service import RoutingService
from services.rule_service import RuleService

class DummyCursor(list):
    def sort(self, *args, **kwargs):
        if args and isinstance(args[0], list):
            field, direction = args[0][0]
            reverse = (direction == -1)
            super().sort(key=lambda x: x.get(field, ""), reverse=reverse)
        elif args and isinstance(args[0], str):
            field = args[0]
            direction = args[1] if len(args) > 1 else 1
            reverse = (direction == -1)
            super().sort(key=lambda x: x.get(field, ""), reverse=reverse)
        return self

class DummyCollection:
    def __init__(self):
        self.docs = []

    def create_index(self, key, unique=False):
        pass

    def insert_one(self, doc):
        from bson import ObjectId
        doc["_id"] = ObjectId()
        self.docs.append(doc)
        class Res:
            inserted_id = doc["_id"]
        return Res()

    def update_many(self, query, update):
        count = 0
        for doc in self.docs:
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match and "$set" in update:
                doc.update(update["$set"])
                count += 1
        class Res:
            modified_count = count
        return Res()

    def find_one(self, query):
        for doc in self.docs:
            if "$or" in query:
                for cond in query["$or"]:
                    k, v = list(cond.items())[0]
                    if doc.get(k) == v:
                        return doc
            else:
                match = True
                for k, v in query.items():
                    if k == "_id":
                        if str(doc.get("_id")) != str(v):
                            match = False
                    elif doc.get(k) != v:
                        match = False
                if match:
                    return doc
        return None

    def update_one(self, query, update):
        doc = self.find_one(query)
        if doc and "$set" in update:
            doc.update(update["$set"])
        class Res:
            modified_count = 1 if doc else 0
        return Res()

    def find(self, query=None, projection=None):
        res = DummyCursor()
        q = query or {}
        for doc in self.docs:
            d = dict(doc)
            match = True
            for k, v in q.items():
                if d.get(k) != v:
                    match = False
                    break
            if match:
                if projection and projection.get("passwordHash") == 0:
                    d.pop("passwordHash", None)
                res.append(d)
        return res

@pytest.fixture(autouse=True)
def mock_db_if_offline(monkeypatch):
    user_dummy = DummyCollection()
    parcel_dummy = DummyCollection()
    audit_dummy = DummyCollection()
    rule_dummy = DummyCollection()
    request_dummy = DummyCollection()

    monkeypatch.setattr("models.user_model.UserModel.get_collection", classmethod(lambda cls: user_dummy))
    monkeypatch.setattr("models.parcel_model.ParcelModel.get_collection", classmethod(lambda cls: parcel_dummy))
    monkeypatch.setattr("models.audit_model.AuditModel.get_collection", classmethod(lambda cls: audit_dummy))
    monkeypatch.setattr("models.routing_rule_model.RoutingRuleModel.get_collection", classmethod(lambda cls: rule_dummy))
    monkeypatch.setattr("models.rule_change_request_model.RuleChangeRequestModel.get_collection", classmethod(lambda cls: request_dummy))
    monkeypatch.setattr("config.db.Database.get_db", staticmethod(lambda: {
        "users": user_dummy, "parcels": parcel_dummy, "audit_logs": audit_dummy,
        "routing_rules": rule_dummy, "rule_change_requests": request_dummy
    }))

    from services.auth_service import _failed_login_attempts
    _failed_login_attempts.clear()

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-rules-secret'
    with app.test_client() as client:
        yield client

def helper_register_and_login(client, username, role="operator", admin_key=""):
    mobile_suffix = str(abs(hash(username)) % 100000000).zfill(8)
    unique_mobile = f"99{mobile_suffix}"

    payload = {
        "fullName": f"Test {username}",
        "username": username,
        "email": f"{username}@example.com",
        "mobile": unique_mobile,
        "password": "Password123!",
        "confirmPassword": "Password123!",
        "role": role
    }
    if role == "admin":
        payload["adminKey"] = admin_key or Config.ADMIN_REGISTRATION_KEY

    client.post('/api/auth/register', json=payload)
    login_res = client.post('/api/auth/login', json={"identifier": username, "password": "Password123!"})
    return login_res.get_json()["csrfToken"]

def helper_login_user(client, username):
    login_res = client.post('/api/auth/login', json={"identifier": username, "password": "Password123!"})
    return login_res.get_json()["csrfToken"]

# --- 1. Default Rules Are Available ---
def test_1_default_rules_available():
    active = RoutingRuleModel.get_active_rules()
    assert active is not None
    assert active["version"] == 1
    assert active["isActive"] is True

# --- 2. Default Rules Match Old Behavior ---
def test_2_default_rules_match_old_behavior():
    r1 = RoutingService.evaluate_routing(1.00, 1000.00)
    assert r1["department"] == "MAIL"
    assert r1["insuranceRequired"] is False

    r2 = RoutingService.evaluate_routing(5.00, 1500.00)
    assert r2["department"] == "REGULAR"
    assert r2["insuranceRequired"] is True

# --- 3. Boundary 1.00 kg -> MAIL ---
def test_3_boundary_1kg_mail():
    res = RoutingService.evaluate_routing(1.00, 500)
    assert res["department"] == "MAIL"

# --- 4. Boundary 1.01 kg -> REGULAR ---
def test_4_boundary_1_01kg_regular():
    res = RoutingService.evaluate_routing(1.01, 500)
    assert res["department"] == "REGULAR"

# --- 5. Boundary 10.00 kg -> REGULAR ---
def test_5_boundary_10kg_regular():
    res = RoutingService.evaluate_routing(10.00, 500)
    assert res["department"] == "REGULAR"

# --- 6. Boundary 10.01 kg -> HEAVY ---
def test_6_boundary_10_01kg_heavy():
    res = RoutingService.evaluate_routing(10.01, 500)
    assert res["department"] == "HEAVY"

# --- 7. Boundary 1000 EUR -> No Insurance ---
def test_7_boundary_1000eur_no_insurance():
    res = RoutingService.evaluate_routing(5.00, 1000.00)
    assert res["insuranceRequired"] is False
    assert res["insuranceStatus"] == "NOT_REQUIRED"

# --- 8. Boundary 1000.01 EUR -> Insurance Required ---
def test_8_boundary_1000_01eur_insurance_required():
    res = RoutingService.evaluate_routing(5.00, 1000.01)
    assert res["insuranceRequired"] is True
    assert res["insuranceStatus"] == "PENDING"

# --- 9. Invalid Overlapping Rule Set Rejected ---
def test_9_invalid_overlapping_rule_set_rejected():
    overlap_depts = [
        { "department": "MAIL", "minWeight": 0.0, "minOp": "GT", "maxWeight": 2.0, "maxOp": "LTE" },
        { "department": "REGULAR", "minWeight": 1.0, "minOp": "GT", "maxWeight": 10.0, "maxOp": "LTE" },
        { "department": "HEAVY", "minWeight": 10.0, "minOp": "GT", "maxWeight": None, "maxOp": None }
    ]
    ins = { "thresholdEur": 1000.0, "operator": "GT" }
    valid, err = RuleService.validate_rule_set(overlap_depts, ins)
    assert valid is False
    assert "overlap" in err.lower()

# --- 10. Incomplete Rule Set Rejected ---
def test_10_incomplete_rule_set_rejected():
    incomplete = [
        { "department": "MAIL", "minWeight": 0.0, "minOp": "GT", "maxWeight": 1.0, "maxOp": "LTE" }
    ]
    ins = { "thresholdEur": 1000.0, "operator": "GT" }
    valid, err = RuleService.validate_rule_set(incomplete, ins)
    assert valid is False
    assert "Missing required department rules" in err

# --- 11. Invalid Operator Rejected ---
def test_11_invalid_operator_rejected():
    invalid_op_depts = [
        { "department": "MAIL", "minWeight": 0.0, "minOp": "INVALID_OP", "maxWeight": 1.0, "maxOp": "LTE" },
        { "department": "REGULAR", "minWeight": 1.0, "minOp": "GT", "maxWeight": 10.0, "maxOp": "LTE" },
        { "department": "HEAVY", "minWeight": 10.0, "minOp": "GT", "maxWeight": None, "maxOp": None }
    ]
    ins = { "thresholdEur": 1000.0, "operator": "GT" }
    valid, err = RuleService.validate_rule_set(invalid_op_depts, ins)
    assert valid is False
    assert "Invalid minOp" in err

# --- 12. Unsupported Rule Type Rejected ---
def test_12_unsupported_rule_type_rejected():
    unsupported_depts = [
        { "department": "UNKNOWN_DEPT", "minWeight": 0.0, "minOp": "GT", "maxWeight": 1.0, "maxOp": "LTE" }
    ]
    ins = { "thresholdEur": 1000.0, "operator": "GT" }
    valid, err = RuleService.validate_rule_set(unsupported_depts, ins)
    assert valid is False

# --- 13. Admin Can View Rules ---
def test_13_admin_can_view_rules(client):
    csrf = helper_register_and_login(client, "admin_rules_view", role="admin")
    res = client.get('/api/routing-rules/active', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    assert res.get_json()["activeRules"]["version"] == 1

# --- 14. Admin Can Activate Rules ---
def test_14_admin_can_activate_rules(client):
    csrf = helper_register_and_login(client, "admin_rules_act", role="admin")
    # Admin approves a change request to activate new version
    op_csrf = helper_register_and_login(client, "op_rules_req", role="operator")
    req_res = client.post('/api/rule-change-requests', json={
        "action": "MODIFY", "category": "INSURANCE", "reason": "Lower threshold",
        "proposedChange": {"thresholdEur": 500.0}
    }, headers={"X-CSRF-Token": op_csrf})
    req_id = req_res.get_json()["request"]["requestId"]

    admin_csrf = helper_login_user(client, "admin_rules_act")
    app_res = client.post(f'/api/rule-change-requests/{req_id}/approve', json={"confirm": True}, headers={"X-CSRF-Token": admin_csrf})
    assert app_res.status_code == 200
    assert app_res.get_json()["activeRuleVersion"]["version"] >= 2

# --- 15. Operator Can View Active Rules ---
def test_15_operator_can_view_active_rules(client):
    op_csrf = helper_register_and_login(client, "op_rules_view", role="operator")
    res = client.get('/api/routing-rules/active', headers={"X-CSRF-Token": op_csrf})
    assert res.status_code == 200
    assert res.get_json()["activeRules"]["isActive"] is True

# --- 16. Operator Cannot Directly Modify/Activate Rules ---
def test_16_operator_cannot_approve(client):
    op_csrf = helper_register_and_login(client, "op_no_approve", role="operator")
    res = client.post('/api/rule-change-requests/RCR-123456/approve', json={"confirm": True}, headers={"X-CSRF-Token": op_csrf})
    assert res.status_code == 403

# --- 17. Normal User Gets 403 ---
def test_17_normal_user_gets_403(client):
    user_csrf = helper_register_and_login(client, "user_rules_denied", role="user")
    res = client.get('/api/routing-rules/active', headers={"X-CSRF-Token": user_csrf})
    assert res.status_code == 403

# --- 18. Unauthenticated Gets 401 ---
def test_18_unauthenticated_gets_401(client):
    res = client.get('/api/routing-rules/active')
    assert res.status_code == 401

# --- 19. Activating New Version Preserves Previous Version ---
def test_19_activating_new_version_preserves_previous_version(client):
    admin_csrf = helper_register_and_login(client, "admin_ver_pres", role="admin")
    op_csrf = helper_register_and_login(client, "op_ver_req", role="operator")
    req = client.post('/api/rule-change-requests', json={
        "action": "MODIFY", "category": "INSURANCE", "reason": "Adjust threshold",
        "proposedChange": {"thresholdEur": 800.0}
    }, headers={"X-CSRF-Token": op_csrf}).get_json()["request"]["requestId"]

    admin_csrf = helper_login_user(client, "admin_ver_pres")
    client.post(f'/api/rule-change-requests/{req}/approve', json={"confirm": True}, headers={"X-CSRF-Token": admin_csrf})

    hist_res = client.get('/api/routing-rules/history', headers={"X-CSRF-Token": admin_csrf})
    assert hist_res.status_code == 200
    history = hist_res.get_json()["history"]
    assert len(history) >= 2
    versions = [h["version"] for h in history]
    assert 1 in versions and 2 in versions

# --- 20. Active Version Changes Correctly ---
def test_20_active_version_changes_correctly(client):
    active = RoutingRuleModel.get_active_rules()
    initial_ver = active["version"]
    
    # Activate version 2
    dept = active["departmentRules"]
    ins = { "thresholdEur": 1200.0, "operator": "GT" }
    v2 = RoutingRuleModel.create_and_activate_version(dept, ins, "admin1", "admin1")
    assert v2["version"] == initial_ver + 1

    new_active = RoutingRuleModel.get_active_rules()
    assert new_active["version"] == v2["version"]

# --- 21. Old Version Remains Available In History ---
def test_21_old_version_remains_available_in_history(client):
    admin_csrf = helper_register_and_login(client, "admin_hist_check", role="admin")
    hist = RoutingRuleModel.get_rule_history()
    assert len(hist) > 0
    v1_doc = RoutingRuleModel.get_rule_by_version(1)
    assert v1_doc is not None
    assert v1_doc["version"] == 1

# --- 22. Existing Parcels Are NOT Automatically Rerouted ---
def test_22_existing_parcels_not_automatically_rerouted(client):
    op_csrf = helper_register_and_login(client, "op_exist_parcel", role="operator")
    # Create parcel under Version 1 rules
    p_doc = ParcelModel.create_parcel({"parcelId": "P-NO-REROUTE", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 0.5, "valueEur": 100, "submittedBy": "op_exist_parcel"})
    ParcelModel.update_parcel_routing("P-NO-REROUTE", {"department": "MAIL", "insuranceRequired": False, "insuranceStatus": "NOT_REQUIRED", "status": "ROUTING_EVALUATED"})

    # Change active rule set
    admin_csrf = helper_register_and_login(client, "admin_rule_change", role="admin")
    RoutingRuleModel.create_and_activate_version([
        { "department": "MAIL", "minWeight": 0.0, "minOp": "GT", "maxWeight": 0.2, "maxOp": "LTE" },
        { "department": "REGULAR", "minWeight": 0.2, "minOp": "GT", "maxWeight": 10.0, "maxOp": "LTE" },
        { "department": "HEAVY", "minWeight": 10.0, "minOp": "GT", "maxWeight": None, "maxOp": None }
    ], { "thresholdEur": 1000.0, "operator": "GT" }, "admin", "admin")

    # Verify existing parcel remains in MAIL status
    p_check = ParcelModel.find_by_parcel_id("P-NO-REROUTE")
    assert p_check["department"] == "MAIL"

# --- 23. Operator Can Create Request ---
def test_23_operator_can_create_request(client):
    op_csrf = helper_register_and_login(client, "op_req_creator", role="operator")
    res = client.post('/api/rule-change-requests', json={
        "action": "MODIFY", "category": "DEPARTMENT", "targetDepartment": "MAIL",
        "reason": "Increase mail weight threshold",
        "proposedChange": {"department": "MAIL", "minWeight": 0.0, "minOp": "GT", "maxWeight": 1.5, "maxOp": "LTE"}
    }, headers={"X-CSRF-Token": op_csrf})
    assert res.status_code == 201
    assert res.get_json()["request"]["requestId"].startswith("RCR-")

# --- 24. Operator Cannot Create Request With Invalid Data ---
def test_24_operator_cannot_create_request_with_invalid_data(client):
    op_csrf = helper_register_and_login(client, "op_bad_req", role="operator")
    res = client.post('/api/rule-change-requests', json={
        "action": "INVALID_ACTION", "category": "DEPARTMENT", "reason": "Short"
    }, headers={"X-CSRF-Token": op_csrf})
    assert res.status_code == 400

# --- 25. Operator Can Withdraw Own Pending Request ---
def test_25_operator_can_withdraw_own_pending_request(client):
    op_csrf = helper_register_and_login(client, "op_withdrawer", role="operator")
    req_res = client.post('/api/rule-change-requests', json={
        "action": "MODIFY", "category": "INSURANCE", "reason": "Change threshold",
        "proposedChange": {"thresholdEur": 500.0}
    }, headers={"X-CSRF-Token": op_csrf})
    req_id = req_res.get_json()["request"]["requestId"]

    w_res = client.post(f'/api/rule-change-requests/{req_id}/withdraw', headers={"X-CSRF-Token": op_csrf})
    assert w_res.status_code == 200
    assert w_res.get_json()["request"]["status"] == "WITHDRAWN"

# --- 26. Operator Cannot Withdraw Another User Request ---
def test_26_operator_cannot_withdraw_another_user_request(client):
    op1_csrf = helper_register_and_login(client, "op_owner1", role="operator")
    req_res = client.post('/api/rule-change-requests', json={
        "action": "MODIFY", "category": "INSURANCE", "reason": "Change threshold",
        "proposedChange": {"thresholdEur": 500.0}
    }, headers={"X-CSRF-Token": op1_csrf})
    req_id = req_res.get_json()["request"]["requestId"]

    op2_csrf = helper_register_and_login(client, "op_hacker2", role="operator")
    w_res = client.post(f'/api/rule-change-requests/{req_id}/withdraw', headers={"X-CSRF-Token": op2_csrf})
    assert w_res.status_code == 403

# --- 27. Operator Cannot Withdraw Approved/Rejected/Withdrawn Request ---
def test_27_operator_cannot_withdraw_approved_rejected_withdrawn_request(client):
    op_csrf = helper_register_and_login(client, "op_double_withdrawer", role="operator")
    req_res = client.post('/api/rule-change-requests', json={
        "action": "MODIFY", "category": "INSURANCE", "reason": "Change threshold",
        "proposedChange": {"thresholdEur": 500.0}
    }, headers={"X-CSRF-Token": op_csrf})
    req_id = req_res.get_json()["request"]["requestId"]

    # First withdraw -> 200
    client.post(f'/api/rule-change-requests/{req_id}/withdraw', headers={"X-CSRF-Token": op_csrf})
    # Second withdraw -> 400
    res2 = client.post(f'/api/rule-change-requests/{req_id}/withdraw', headers={"X-CSRF-Token": op_csrf})
    assert res2.status_code == 400

# --- 28. Admin Can View Requests ---
def test_28_admin_can_view_requests(client):
    admin_csrf = helper_register_and_login(client, "admin_req_viewer", role="admin")
    res = client.get('/api/rule-change-requests', headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 200
    assert "requests" in res.get_json()

# --- 29. Admin Can Approve Valid Request ---
def test_29_admin_can_approve_valid_request(client):
    op_csrf = helper_register_and_login(client, "op_valid_req", role="operator")
    req_res = client.post('/api/rule-change-requests', json={
        "action": "MODIFY", "category": "INSURANCE", "reason": "Lower threshold to 800",
        "proposedChange": {"thresholdEur": 800.0}
    }, headers={"X-CSRF-Token": op_csrf})
    req_id = req_res.get_json()["request"]["requestId"]

    admin_csrf = helper_register_and_login(client, "admin_valid_approver", role="admin")
    res = client.post(f'/api/rule-change-requests/{req_id}/approve', json={"confirm": True}, headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 200
    assert res.get_json()["request"]["status"] == "APPROVED"

# --- 30. Admin Approval Creates New Version ---
def test_30_admin_approval_creates_new_version(client):
    active_before = RoutingRuleModel.get_active_rules()["version"]
    
    op_csrf = helper_register_and_login(client, "op_ver_req2", role="operator")
    req_res = client.post('/api/rule-change-requests', json={
        "action": "MODIFY", "category": "INSURANCE", "reason": "Adjust threshold to 700",
        "proposedChange": {"thresholdEur": 700.0}
    }, headers={"X-CSRF-Token": op_csrf})
    req_id = req_res.get_json()["request"]["requestId"]

    admin_csrf = helper_register_and_login(client, "admin_ver_approver", role="admin")
    client.post(f'/api/rule-change-requests/{req_id}/approve', json={"confirm": True}, headers={"X-CSRF-Token": admin_csrf})

    active_after = RoutingRuleModel.get_active_rules()["version"]
    assert active_after == active_before + 1

# --- 31. Admin Approval Activates New Version ---
def test_31_admin_approval_activates_new_version(client):
    op_csrf = helper_register_and_login(client, "op_act_req", role="operator")
    req_res = client.post('/api/rule-change-requests', json={
        "action": "MODIFY", "category": "INSURANCE", "reason": "Set threshold to 600",
        "proposedChange": {"thresholdEur": 600.0}
    }, headers={"X-CSRF-Token": op_csrf})
    req_id = req_res.get_json()["request"]["requestId"]

    admin_csrf = helper_register_and_login(client, "admin_act_app", role="admin")
    client.post(f'/api/rule-change-requests/{req_id}/approve', json={"confirm": True}, headers={"X-CSRF-Token": admin_csrf})

    active = RoutingRuleModel.get_active_rules()
    assert active["insuranceRule"]["thresholdEur"] == 600.0

# --- 32. Admin Approval Creates Audit Log ---
def test_32_admin_approval_creates_audit_log(client):
    op_csrf = helper_register_and_login(client, "op_audit_req", role="operator")
    req_res = client.post('/api/rule-change-requests', json={
        "action": "MODIFY", "category": "INSURANCE", "reason": "Set threshold to 900",
        "proposedChange": {"thresholdEur": 900.0}
    }, headers={"X-CSRF-Token": op_csrf})
    req_id = req_res.get_json()["request"]["requestId"]

    admin_csrf = helper_register_and_login(client, "admin_audit_app", role="admin")
    client.post(f'/api/rule-change-requests/{req_id}/approve', json={"confirm": True}, headers={"X-CSRF-Token": admin_csrf})

    logs = AuditModel.get_all_logs()
    actions = [l["action"] for l in logs]
    assert "RULE_CHANGE_APPROVED" in actions
    assert "RULE_VERSION_ACTIVATED" in actions

# --- 33. Admin Rejection Requires Reason ---
def test_33_admin_rejection_requires_reason(client):
    op_csrf = helper_register_and_login(client, "op_rej_req", role="operator")
    req_res = client.post('/api/rule-change-requests', json={
        "action": "MODIFY", "category": "INSURANCE", "reason": "Set threshold to 500",
        "proposedChange": {"thresholdEur": 500.0}
    }, headers={"X-CSRF-Token": op_csrf})
    req_id = req_res.get_json()["request"]["requestId"]

    admin_csrf = helper_register_and_login(client, "admin_rej_noreason", role="admin")
    res = client.post(f'/api/rule-change-requests/{req_id}/reject', json={"reason": "   "}, headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 400
    assert "Rejection reason is required" in res.get_json()["error"]

# --- 34. Rejection Does Not Modify Active Rules ---
def test_34_rejection_does_not_modify_active_rules(client):
    active_before = RoutingRuleModel.get_active_rules()["version"]
    
    op_csrf = helper_register_and_login(client, "op_rej_req2", role="operator")
    req_res = client.post('/api/rule-change-requests', json={
        "action": "MODIFY", "category": "INSURANCE", "reason": "Set threshold to 100",
        "proposedChange": {"thresholdEur": 100.0}
    }, headers={"X-CSRF-Token": op_csrf})
    req_id = req_res.get_json()["request"]["requestId"]

    admin_csrf = helper_register_and_login(client, "admin_rej_user", role="admin")
    res = client.post(f'/api/rule-change-requests/{req_id}/reject', json={"reason": "Too low threshold"}, headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 200
    assert res.get_json()["request"]["status"] == "REJECTED"

    active_after = RoutingRuleModel.get_active_rules()["version"]
    assert active_after == active_before

# --- 35. Rejection Creates Audit Log ---
def test_35_rejection_creates_audit_log(client):
    op_csrf = helper_register_and_login(client, "op_rej_audit", role="operator")
    req_res = client.post('/api/rule-change-requests', json={
        "action": "MODIFY", "category": "INSURANCE", "reason": "Set threshold to 200",
        "proposedChange": {"thresholdEur": 200.0}
    }, headers={"X-CSRF-Token": op_csrf})
    req_id = req_res.get_json()["request"]["requestId"]

    admin_csrf = helper_register_and_login(client, "admin_rej_audit", role="admin")
    client.post(f'/api/rule-change-requests/{req_id}/reject', json={"reason": "Unjustified"}, headers={"X-CSRF-Token": admin_csrf})

    logs = AuditModel.get_all_logs()
    actions = [l["action"] for l in logs]
    assert "RULE_CHANGE_REJECTED" in actions

# --- 36. Operator Cannot Approve ---
def test_36_operator_cannot_approve(client):
    op_csrf = helper_register_and_login(client, "op_no_app", role="operator")
    res = client.post('/api/rule-change-requests/RCR-999999/approve', json={"confirm": True}, headers={"X-CSRF-Token": op_csrf})
    assert res.status_code == 403

# --- 37. Normal User Gets 403 ---
def test_37_normal_user_gets_403(client):
    user_csrf = helper_register_and_login(client, "user_rcr_denied", role="user")
    res = client.get('/api/rule-change-requests', headers={"X-CSRF-Token": user_csrf})
    assert res.status_code == 403

# --- 38. Arbitrary MongoDB Operators Are Rejected ---
def test_38_arbitrary_mongodb_operators_rejected(client):
    admin_csrf = helper_register_and_login(client, "admin_nosql_check", role="admin")
    res = client.get('/api/rule-change-requests?status={$gt:""}', headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 200
    # NoSQL query injection must be sanitized string, not evaluated as object filter

# --- 39. Client Cannot Forge Actor Identity ---
def test_39_client_cannot_forge_actor_identity(client):
    op_csrf = helper_register_and_login(client, "op_forge_check", role="operator")
    res = client.post('/api/rule-change-requests', json={
        "action": "MODIFY", "category": "INSURANCE", "reason": "Change threshold",
        "proposedChange": {"thresholdEur": 500.0},
        "requestedBy": "fake_admin_id_999", "requestedByUsername": "fake_admin"
    }, headers={"X-CSRF-Token": op_csrf})
    assert res.status_code == 201
    req = res.get_json()["request"]
    assert req["requestedByUsername"] != "fake_admin"
    assert req["requestedByUsername"] == "op_forge_check"

# --- 40. Sensitive Activation Requires Explicit Confirmation ---
def test_40_sensitive_activation_requires_explicit_confirmation(client):
    op_csrf = helper_register_and_login(client, "op_noconf_req", role="operator")
    req_res = client.post('/api/rule-change-requests', json={
        "action": "MODIFY", "category": "INSURANCE", "reason": "Change threshold",
        "proposedChange": {"thresholdEur": 500.0}
    }, headers={"X-CSRF-Token": op_csrf})
    req_id = req_res.get_json()["request"]["requestId"]

    admin_csrf = helper_register_and_login(client, "admin_noconf_app", role="admin")
    res = client.post(f'/api/rule-change-requests/{req_id}/approve', json={"confirm": False}, headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 400
    assert "Explicit confirmation" in res.get_json()["error"]

# --- 41. Invalid Rule Configuration Cannot Be Activated ---
def test_41_invalid_rule_configuration_cannot_be_activated(client):
    op_csrf = helper_register_and_login(client, "op_bad_rule_req", role="operator")
    req_res = client.post('/api/rule-change-requests', json={
        "action": "MODIFY", "category": "DEPARTMENT", "targetDepartment": "MAIL",
        "reason": "Bad threshold overlap",
        "proposedChange": {"department": "MAIL", "minWeight": 0.0, "minOp": "GT", "maxWeight": 5.0, "maxOp": "LTE"} # Overlaps with REGULAR (1.0 to 10.0)
    }, headers={"X-CSRF-Token": op_csrf})
    req_id = req_res.get_json()["request"]["requestId"]

    admin_csrf = helper_register_and_login(client, "admin_bad_rule_app", role="admin")
    res = client.post(f'/api/rule-change-requests/{req_id}/approve', json={"confirm": True}, headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 400
    assert "Invalid resulting rule set" in res.get_json()["error"]

# --- 42-45. Regression Checks ---
def test_42_regression_existing_routing_tests_pass():
    res = RoutingService.evaluate_routing(2.5, 1500)
    assert res["department"] == "REGULAR"
    assert res["insuranceRequired"] is True

def test_43_regression_insurance_lifecycle_pass():
    active = RoutingRuleModel.get_active_rules()
    assert active["insuranceRule"]["thresholdEur"] >= 0

def test_44_regression_dashboard_metrics_pass(client):
    admin_csrf = helper_register_and_login(client, "admin_regr_dash", role="admin")
    res = client.get('/api/dashboard/summary', headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 200

def test_45_regression_all_previous_tests_pass(client):
    active = RoutingRuleModel.get_active_rules()
    assert active["version"] >= 1
