import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config.settings import Config
from models.audit_model import AuditModel

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

    def find(self, query, projection=None):
        res = DummyCursor()
        for doc in self.docs:
            d = dict(doc)
            if projection and projection.get("passwordHash") == 0:
                d.pop("passwordHash", None)
            res.append(d)
        return res

@pytest.fixture(autouse=True)
def mock_db_if_offline(monkeypatch):
    user_dummy = DummyCollection()
    parcel_dummy = DummyCollection()
    audit_dummy = DummyCollection()

    monkeypatch.setattr("models.user_model.UserModel.get_collection", classmethod(lambda cls: user_dummy))
    monkeypatch.setattr("models.parcel_model.ParcelModel.get_collection", classmethod(lambda cls: parcel_dummy))
    monkeypatch.setattr("models.audit_model.AuditModel.get_collection", classmethod(lambda cls: audit_dummy))

    from services.auth_service import _failed_login_attempts
    _failed_login_attempts.clear()

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-lifecycle-secret'
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

def helper_create_high_value_parcel_awaiting_insurance(client, op_csrf):
    create_res = client.post('/api/parcels', json={
        "senderName": "Alice", "senderContact": "123", "receiverName": "Bob", "receiverContact": "456",
        "origin": "Berlin", "destination": "Munich", "weightKg": 2.0, "valueEur": 2000.0
    }, headers={"X-CSRF-Token": op_csrf})
    parcel_id = create_res.get_json()["parcel"]["parcelId"]
    client.post(f'/api/parcels/{parcel_id}/route', headers={"X-CSRF-Token": op_csrf})
    return parcel_id

# --- 1. Insurance Approval Tests ---

def test_admin_can_approve_insurance(client):
    op_csrf = helper_register_and_login(client, "op_ins_app", role="operator")
    parcel_id = helper_create_high_value_parcel_awaiting_insurance(client, op_csrf)

    admin_csrf = helper_register_and_login(client, "admin_ins_app", role="admin")

    res = client.post(f'/api/parcels/{parcel_id}/insurance/approve', headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 200
    p = res.get_json()["parcel"]
    assert p["status"] == "INSURANCE_APPROVED"
    assert p["insuranceStatus"] == "APPROVED"

    # Verify Audit log recorded
    logs = AuditModel.get_all_logs()
    assert len(logs) > 0
    assert logs[0]["action"] == "Insurance Approved"
    assert logs[0]["parcelId"] == parcel_id

def test_operator_cannot_approve_insurance(client):
    op_csrf = helper_register_and_login(client, "op_denied_ins", role="operator")
    parcel_id = helper_create_high_value_parcel_awaiting_insurance(client, op_csrf)

    res = client.post(f'/api/parcels/{parcel_id}/insurance/approve', headers={"X-CSRF-Token": op_csrf})
    assert res.status_code == 403
    assert "Access denied" in res.get_json()["error"]

def test_normal_user_registration_rejected_insurance(client):
    res = client.post('/api/auth/register', json={
        "fullName": "User Ins App", "username": "user_ins_app", "email": "ins_user@example.com",
        "mobile": "9955443322", "password": "Password123!", "confirmPassword": "Password123!",
        "role": "user"
    })
    assert res.status_code == 400
    assert "Allowed roles are 'operator' and 'admin'." in res.get_json()["error"]

def test_unauthenticated_cannot_approve_insurance(client):
    res = client.post('/api/parcels/PCL-SOMEID/insurance/approve')
    assert res.status_code == 401

# --- 2. Insurance Rejection Tests ---

def test_admin_can_reject_insurance_with_reason(client):
    op_csrf = helper_register_and_login(client, "op_ins_rej", role="operator")
    parcel_id = helper_create_high_value_parcel_awaiting_insurance(client, op_csrf)

    admin_csrf = helper_register_and_login(client, "admin_ins_rej", role="admin")

    res = client.post(f'/api/parcels/{parcel_id}/insurance/reject', json={"reason": "High risk valuation"}, headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 200
    p = res.get_json()["parcel"]
    assert p["status"] == "INSURANCE_REJECTED"
    assert p["insuranceStatus"] == "REJECTED"
    assert p["failureReason"] == "High risk valuation"

def test_rejection_without_reason_returns_400(client):
    op_csrf = helper_register_and_login(client, "op_ins_noreason", role="operator")
    parcel_id = helper_create_high_value_parcel_awaiting_insurance(client, op_csrf)

    admin_csrf = helper_register_and_login(client, "admin_ins_noreason", role="admin")

    res = client.post(f'/api/parcels/{parcel_id}/insurance/reject', json={"reason": "   "}, headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 400
    assert "Rejection reason is required" in res.get_json()["error"]

# --- 3. Invalid Insurance Actions ---

def test_cannot_approve_parcel_not_requiring_insurance(client):
    op_csrf = helper_register_and_login(client, "op_low_val", role="operator")

    create_res = client.post('/api/parcels', json={
        "senderName": "Alice", "senderContact": "123", "receiverName": "Bob", "receiverContact": "456",
        "origin": "Berlin", "destination": "Munich", "weightKg": 2.0, "valueEur": 500.0
    }, headers={"X-CSRF-Token": op_csrf})
    parcel_id = create_res.get_json()["parcel"]["parcelId"]
    client.post(f'/api/parcels/{parcel_id}/route', headers={"X-CSRF-Token": op_csrf})

    admin_csrf = helper_register_and_login(client, "admin_low_val", role="admin")

    res = client.post(f'/api/parcels/{parcel_id}/insurance/approve', headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 400
    assert "Cannot approve insurance" in res.get_json()["error"]

def test_cannot_approve_already_rejected_insurance(client):
    op_csrf = helper_register_and_login(client, "op_already_rej", role="operator")
    parcel_id = helper_create_high_value_parcel_awaiting_insurance(client, op_csrf)

    admin_csrf = helper_register_and_login(client, "admin_already_rej", role="admin")

    # Reject first
    client.post(f'/api/parcels/{parcel_id}/insurance/reject', json={"reason": "Risk"}, headers={"X-CSRF-Token": admin_csrf})

    # Try approve second
    res = client.post(f'/api/parcels/{parcel_id}/insurance/approve', headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 400

def test_cannot_reject_already_approved_insurance(client):
    op_csrf = helper_register_and_login(client, "op_already_app", role="operator")
    parcel_id = helper_create_high_value_parcel_awaiting_insurance(client, op_csrf)

    admin_csrf = helper_register_and_login(client, "admin_already_app", role="admin")

    # Approve first
    client.post(f'/api/parcels/{parcel_id}/insurance/approve', headers={"X-CSRF-Token": admin_csrf})

    # Try reject second
    res = client.post(f'/api/parcels/{parcel_id}/insurance/reject', json={"reason": "Changed mind"}, headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 400

def test_insurance_action_on_nonexistent_parcel_returns_404(client):
    admin_csrf = helper_register_and_login(client, "admin_404_ins", role="admin")
    res = client.post('/api/parcels/PCL-NOEXIST/insurance/approve', headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 404

# --- 4. Valid & Invalid Lifecycle Transitions ---

def test_complete_valid_parcel_lifecycle_progression(client):
    op_csrf = helper_register_and_login(client, "op_lifecycle", role="operator")
    parcel_id = helper_create_high_value_parcel_awaiting_insurance(client, op_csrf)

    admin_csrf = helper_register_and_login(client, "admin_lifecycle", role="admin")

    # 1. AWAITING_INSURANCE -> INSURANCE_APPROVED (Admin)
    res_app = client.post(f'/api/parcels/{parcel_id}/insurance/approve', headers={"X-CSRF-Token": admin_csrf})
    assert res_app.status_code == 200
    assert res_app.get_json()["parcel"]["status"] == "INSURANCE_APPROVED"

    # 2. INSURANCE_APPROVED -> ASSIGNED (Operator or Admin)
    # Log back in as operator
    op_csrf2 = helper_register_and_login(client, "op_lifecycle", role="operator")
    res_ass = client.post(f'/api/parcels/{parcel_id}/assign', headers={"X-CSRF-Token": op_csrf2})
    assert res_ass.status_code == 200
    assert res_ass.get_json()["parcel"]["status"] == "ASSIGNED"

    # 3. ASSIGNED -> IN_PROCESSING (Operator or Admin)
    res_proc = client.post(f'/api/parcels/{parcel_id}/start-processing', headers={"X-CSRF-Token": op_csrf2})
    assert res_proc.status_code == 200
    assert res_proc.get_json()["parcel"]["status"] == "IN_PROCESSING"

    # 4. IN_PROCESSING -> COMPLETED (Operator or Admin)
    res_comp = client.post(f'/api/parcels/{parcel_id}/complete', headers={"X-CSRF-Token": op_csrf2})
    assert res_comp.status_code == 200
    assert res_comp.get_json()["parcel"]["status"] == "COMPLETED"

def test_invalid_lifecycle_transitions_rejected(client):
    op_csrf = helper_register_and_login(client, "op_invalid_trans", role="operator")
    parcel_id = helper_create_high_value_parcel_awaiting_insurance(client, op_csrf)

    # Invalid: AWAITING_INSURANCE -> COMPLETED
    res1 = client.post(f'/api/parcels/{parcel_id}/complete', headers={"X-CSRF-Token": op_csrf})
    assert res1.status_code == 400
    assert "Invalid parcel status transition" in res1.get_json()["error"]

    admin_csrf = helper_register_and_login(client, "admin_invalid_trans", role="admin")

    # Approve & complete full chain
    client.post(f'/api/parcels/{parcel_id}/insurance/approve', headers={"X-CSRF-Token": admin_csrf})
    client.post(f'/api/parcels/{parcel_id}/assign', headers={"X-CSRF-Token": admin_csrf})
    client.post(f'/api/parcels/{parcel_id}/start-processing', headers={"X-CSRF-Token": admin_csrf})
    client.post(f'/api/parcels/{parcel_id}/complete', headers={"X-CSRF-Token": admin_csrf})

    # Invalid: COMPLETED -> RECEIVED
    res2 = client.post(f'/api/parcels/{parcel_id}/assign', headers={"X-CSRF-Token": admin_csrf})
    assert res2.status_code == 400

def test_operator_can_assign_start_processing_and_complete(client):
    op_csrf = helper_register_and_login(client, "op_ops", role="operator")
    
    # Low-value parcel (ROUTING_EVALUATED)
    create_res = client.post('/api/parcels', json={
        "senderName": "Alice", "senderContact": "123", "receiverName": "Bob", "receiverContact": "456",
        "origin": "Berlin", "destination": "Munich", "weightKg": 2.0, "valueEur": 100.0
    }, headers={"X-CSRF-Token": op_csrf})
    parcel_id = create_res.get_json()["parcel"]["parcelId"]
    client.post(f'/api/parcels/{parcel_id}/route', headers={"X-CSRF-Token": op_csrf})

    # Assign -> Start Processing -> Complete
    r1 = client.post(f'/api/parcels/{parcel_id}/assign', headers={"X-CSRF-Token": op_csrf})
    assert r1.status_code == 200
    r2 = client.post(f'/api/parcels/{parcel_id}/start-processing', headers={"X-CSRF-Token": op_csrf})
    assert r2.status_code == 200
    r3 = client.post(f'/api/parcels/{parcel_id}/complete', headers={"X-CSRF-Token": op_csrf})
    assert r3.status_code == 200

def test_normal_user_registration_rejected_lifecycle(client):
    res = client.post('/api/auth/register', json={
        "fullName": "User Denied", "username": "user_denied", "email": "user_denied@example.com",
        "mobile": "9955443311", "password": "Password123!", "confirmPassword": "Password123!",
        "role": "user"
    })
    assert res.status_code == 400
    assert "Allowed roles are 'operator' and 'admin'." in res.get_json()["error"]
