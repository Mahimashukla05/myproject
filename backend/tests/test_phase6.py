import pytest
import sys
import os
import json
import io
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config.settings import Config
from config.db import Database
from models.parcel_model import ParcelModel
from models.audit_model import AuditModel
from models.user_model import UserModel

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
        for d in self.docs:
            if "$set" in update:
                d.update(update["$set"])
                count += 1
        class Res:
            modified_count = count
        return Res()

    def update_one(self, query, update):
        doc = self.find_one(query)
        if doc and "$set" in update:
            doc.update(update["$set"])
        class Res:
            modified_count = 1 if doc else 0
        return Res()

    def delete_many(self, query=None):
        if not query:
            self.docs.clear()
        else:
            self.docs = [d for d in self.docs if not all(d.get(k) == v for k, v in query.items())]

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

    def find(self, query=None, projection=None):
        res = DummyCursor()
        q = query or {}
        for doc in self.docs:
            d = dict(doc)
            match = True
            for k, v in q.items():
                if k == "details.outcome":
                    if isinstance(v, dict) and "$in" in v:
                        if d.get("details", {}).get("outcome") not in v["$in"]:
                            match = False
                            break
                elif k == "submittedAt":
                    if isinstance(v, dict) and "$gte" in v:
                        if d.get("submittedAt", "") < v["$gte"]:
                            match = False
                            break
                        if "$lt" in v and d.get("submittedAt", "") >= v["$lt"]:
                            match = False
                            break
                elif d.get(k) != v:
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
    monkeypatch.setattr("config.db.Database.connect", lambda: None)
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
    app.config['SECRET_KEY'] = 'test-phase6-secret'
    with app.test_client() as client:
        yield client

def helper_register_and_login(client, username, role="operator"):
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
        payload["adminKey"] = Config.ADMIN_REGISTRATION_KEY

    client.post('/api/auth/register', json=payload)
    login_res = client.post('/api/auth/login', json={"identifier": username, "password": "Password123!"})
    return login_res

# ============================================================================
# 1. AUDIT LOGS TESTS
# ============================================================================
def test_audit_logs_rbac(client):
    # Unauthenticated -> 401
    resp = client.get('/api/admin/audit-logs')
    assert resp.status_code == 401

    # Normal user registration -> 400
    user_reg = client.post('/api/auth/register', json={
        "fullName": "User 1", "username": "user1", "email": "user1@example.com",
        "mobile": "9911223344", "password": "Password123!", "confirmPassword": "Password123!",
        "role": "user"
    })
    assert user_reg.status_code == 400

    # Operator -> 403
    helper_register_and_login(client, "operator1", "operator")
    resp = client.get('/api/admin/audit-logs')
    assert resp.status_code == 403

    # Admin -> 200
    helper_register_and_login(client, "admin1", "admin")
    resp = client.get('/api/admin/audit-logs')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "logs" in data
    assert "page" in data
    assert "limit" in data
    assert "total" in data
    assert "totalPages" in data

def test_audit_logs_pagination_and_sorting(client):
    helper_register_and_login(client, "admin1", "admin")

    # Seed audit logs
    for i in range(25):
        AuditModel.log_event(
            actor_id=f"user_{i}",
            actor_username=f"user_{i}",
            actor_role="operator",
            action="TEST_ACTION",
            parcel_id=f"P-{i}"
        )

    # Default page 1, limit 20
    resp = client.get('/api/admin/audit-logs')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["logs"]) == 20
    assert data["total"] >= 25
    assert data["page"] == 1
    assert data["limit"] == 20

    # Page 2
    resp = client.get('/api/admin/audit-logs?page=2&limit=20')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["logs"]) >= 5
    assert data["page"] == 2

    # Verify sorting (newest first)
    timestamps = [l["timestamp"] for l in data["logs"]]
    assert timestamps == sorted(timestamps, reverse=True)

def test_audit_logs_filters_and_injection_safety(client):
    helper_register_and_login(client, "admin1", "admin")

    AuditModel.log_event("1", "operator1", "operator", "BATCH_UPLOAD", None, {"outcome": "SUCCESS"})
    AuditModel.log_event("2", "admin1", "admin", "Insurance Approved", "P-100")

    # Filter by action
    resp = client.get('/api/admin/audit-logs?action=BATCH_UPLOAD')
    data = resp.get_json()
    assert data["total"] == 1
    assert data["logs"][0]["action"] == "BATCH_UPLOAD"

    # Filter by actorUsername
    resp = client.get('/api/admin/audit-logs?actorUsername=admin1')
    data = resp.get_json()
    assert data["total"] >= 1

    # Injection safe filter attempt: MongoDB query object passed as string
    resp = client.get('/api/admin/audit-logs?action={$gt:""}')
    data = resp.get_json()
    assert data["total"] == 0


# ============================================================================
# 2. BATCH UPLOAD AUDIT EVENT TESTS
# ============================================================================
def test_batch_upload_audit_events(client):
    login_res = helper_register_and_login(client, "operator1", "operator")
    csrf_token = login_res.get_json()["csrfToken"]
    headers = {"X-CSRF-Token": csrf_token}

    # A. Successful Batch
    valid_json = json.dumps({"parcels": [{
        "parcelId": "P-BATCH-1",
        "senderName": "Alice", "senderContact": "123",
        "receiverName": "Bob", "receiverContact": "456",
        "origin": "NYC", "destination": "LAX",
        "weightKg": 2.5, "valueEur": 100.0
    }]})
    file_data = (io.BytesIO(valid_json.encode('utf-8')), 'test_valid.json')
    resp = client.post('/api/parcels/batch', data={'file': file_data}, headers=headers, content_type='multipart/form-data')
    assert resp.status_code == 200

    logs = AuditModel.get_all_logs()
    batch_logs = [l for l in logs if l.get("action") == "BATCH_UPLOAD"]
    assert len(batch_logs) >= 1
    assert batch_logs[0]["details"]["outcome"] == "SUCCESS"
    assert batch_logs[0]["details"]["successful"] == 1
    assert batch_logs[0]["details"]["failed"] == 0
    assert batch_logs[0]["actorUsername"] == "operator1"

    # Verify newly created parcel remains RECEIVED and not routed
    p = ParcelModel.find_by_parcel_id("P-BATCH-1")
    assert p["status"] == "RECEIVED"
    assert p["department"] is None

    # B. Format Error Batch (Malformed JSON)
    bad_json = "{ invalid json"
    file_data = (io.BytesIO(bad_json.encode('utf-8')), 'bad.json')
    resp = client.post('/api/parcels/batch', data={'file': file_data}, headers=headers, content_type='multipart/form-data')
    assert resp.status_code == 400

    logs = AuditModel.get_all_logs()
    batch_logs = [l for l in logs if l.get("action") == "BATCH_UPLOAD"]
    assert len(batch_logs) >= 2
    assert batch_logs[0]["details"]["outcome"] == "FORMAT_ERROR"

    # C. Partial Failure Batch
    partial_json = json.dumps({"parcels": [
        {
            "parcelId": "P-BATCH-2",
            "senderName": "Alice", "senderContact": "123",
            "receiverName": "Bob", "receiverContact": "456",
            "origin": "NYC", "destination": "LAX",
            "weightKg": 2.5, "valueEur": 100.0
        },
        {
            "parcelId": "P-BATCH-2", # Duplicate ID -> FAILED
            "senderName": "Alice", "senderContact": "123",
            "receiverName": "Bob", "receiverContact": "456",
            "origin": "NYC", "destination": "LAX",
            "weightKg": 2.5, "valueEur": 100.0
        }
    ]})
    file_data = (io.BytesIO(partial_json.encode('utf-8')), 'partial.json')
    resp = client.post('/api/parcels/batch', data={'file': file_data}, headers=headers, content_type='multipart/form-data')
    assert resp.status_code == 200

    logs = AuditModel.get_all_logs()
    batch_logs = [l for l in logs if l.get("action") == "BATCH_UPLOAD"]
    assert len(batch_logs) >= 3
    assert batch_logs[0]["details"]["outcome"] == "PARTIAL_FAILURE"
    assert batch_logs[0]["details"]["successful"] == 1
    assert batch_logs[0]["details"]["failed"] == 1

    # D. Missing file parameter -> returns 400 and creates exactly one BATCH_UPLOAD event (FORMAT_ERROR, UNKNOWN)
    resp = client.post('/api/parcels/batch', data={}, headers=headers, content_type='multipart/form-data')
    assert resp.status_code == 400
    logs = AuditModel.get_all_logs()
    latest_log = logs[0]
    assert latest_log["action"] == "BATCH_UPLOAD"
    assert latest_log["details"]["outcome"] == "FORMAT_ERROR"
    assert latest_log["details"]["fileType"] == "UNKNOWN"

    # E. Empty filename -> returns 400 and creates exactly one BATCH_UPLOAD event (FORMAT_ERROR, UNKNOWN)
    empty_file = (io.BytesIO(b"some data"), '')
    resp = client.post('/api/parcels/batch', data={'file': empty_file}, headers=headers, content_type='multipart/form-data')
    assert resp.status_code == 400
    logs = AuditModel.get_all_logs()
    latest_log = logs[0]
    assert latest_log["action"] == "BATCH_UPLOAD"
    assert latest_log["details"]["outcome"] == "FORMAT_ERROR"
    assert latest_log["details"]["fileType"] == "UNKNOWN"


# ============================================================================
# 3. OPERATOR WORK ALERTS TESTS
# ============================================================================
def test_operator_alerts_scoping_and_content(client):
    # Register & login Operator 1
    helper_register_and_login(client, "operator1", "operator")
    op1 = UserModel.find_by_username("operator1")

    # Operator 1 submits a failed parcel and an insurance rejected parcel
    p_fail = ParcelModel.create_parcel({
        "parcelId": "P-OP1-FAIL",
        "senderName": "A", "senderContact": "1",
        "receiverName": "B", "receiverContact": "2",
        "origin": "X", "destination": "Y",
        "weightKg": 1.0, "valueEur": 10.0,
        "submittedBy": str(op1["_id"])
    })
    ParcelModel.update_parcel_status("P-OP1-FAIL", "FAILED", {"failureReason": "Damaged label"})

    p_ins_rej = ParcelModel.create_parcel({
        "parcelId": "P-OP1-REJ",
        "senderName": "A", "senderContact": "1",
        "receiverName": "B", "receiverContact": "2",
        "origin": "X", "destination": "Y",
        "weightKg": 1.0, "valueEur": 2000.0,
        "submittedBy": str(op1["_id"])
    })
    ParcelModel.update_parcel_status("P-OP1-REJ", "INSURANCE_REJECTED", {"insuranceStatus": "REJECTED"})

    # Batch logs for Operator 1
    AuditModel.log_event(op1["_id"], "operator1", "operator", "BATCH_UPLOAD", None, {
        "fileType": ".json", "total": 5, "successful": 3, "failed": 2, "outcome": "PARTIAL_FAILURE"
    })

    # Register & login Operator 2
    helper_register_and_login(client, "operator2", "operator")
    op2 = UserModel.find_by_username("operator2")

    p_fail2 = ParcelModel.create_parcel({
        "parcelId": "P-OP2-FAIL",
        "senderName": "A", "senderContact": "1",
        "receiverName": "B", "receiverContact": "2",
        "origin": "X", "destination": "Y",
        "weightKg": 1.0, "valueEur": 10.0,
        "submittedBy": str(op2["_id"])
    })
    ParcelModel.update_parcel_status("P-OP2-FAIL", "FAILED", {"failureReason": "Lost in transit"})

    AuditModel.log_event(op2["_id"], "operator2", "operator", "BATCH_UPLOAD", None, {
        "fileType": ".xml", "total": 0, "successful": 0, "failed": 0, "outcome": "FORMAT_ERROR"
    })

    # Operator 2 view
    resp = client.get('/api/operator/alerts')
    assert resp.status_code == 200
    data2 = resp.get_json()

    assert data2["failedParcelsCount"] == 1
    assert data2["failedParcels"][0]["parcelId"] == "P-OP2-FAIL"
    assert data2["batchAlertsCount"] == 1
    assert data2["batchAlertsSummary"]["formatErrors"] == 1
    assert data2["batchAlertsSummary"]["partialFailures"] == 0

    # Operator 1 view
    helper_register_and_login(client, "operator1", "operator")
    resp = client.get('/api/operator/alerts')
    assert resp.status_code == 200
    data1 = resp.get_json()

    assert data1["failedParcelsCount"] == 1
    assert data1["failedParcels"][0]["parcelId"] == "P-OP1-FAIL"
    assert data1["insuranceRejectionsCount"] == 1
    assert data1["batchAlertsCount"] == 1
    assert data1["batchAlertsSummary"]["partialFailures"] == 1
    assert data1["batchAlertsSummary"]["formatErrors"] == 0

    # Normal user registration -> 400
    user_reg = client.post('/api/auth/register', json={
        "fullName": "User 1", "username": "user1_op_alerts", "email": "user1_op_alerts@example.com",
        "mobile": "9911223366", "password": "Password123!", "confirmPassword": "Password123!",
        "role": "user"
    })
    assert user_reg.status_code == 400

    # Admin user view -> 403 (strictly Operator-only endpoint)
    helper_register_and_login(client, "admin1", "admin")
    resp = client.get('/api/operator/alerts')
    assert resp.status_code == 403


# ============================================================================
# 4. ADMIN SYSTEM ALERTS TESTS
# ============================================================================

def test_admin_alerts_rbac(client):
    resp = client.get('/api/admin/alerts')
    assert resp.status_code == 401

    user_reg = client.post('/api/auth/register', json={
        "fullName": "User 1", "username": "user1_alerts", "email": "user1_alerts@example.com",
        "mobile": "9911223355", "password": "Password123!", "confirmPassword": "Password123!",
        "role": "user"
    })
    assert user_reg.status_code == 400

    helper_register_and_login(client, "operator1", "operator")
    resp = client.get('/api/admin/alerts')
    assert resp.status_code == 403

    helper_register_and_login(client, "admin1", "admin")
    resp = client.get('/api/admin/alerts')
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True

def test_admin_alerts_failure_rate_spike(client):
    helper_register_and_login(client, "admin1", "admin")
    op = UserModel.find_by_username("admin1")
    coll = ParcelModel.get_collection()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Case A: Exactly 15% (3 failed out of 20 total) -> NO ALERT
    for i in range(20):
        status = "FAILED" if i < 3 else "COMPLETED"
        doc = {
            "parcelId": f"P-FAIL-{i}",
            "senderName": "A", "senderContact": "1",
            "receiverName": "B", "receiverContact": "2",
            "origin": "X", "destination": "Y",
            "weightKg": 1.0, "valueEur": 10.0,
            "department": "MAIL", "insuranceRequired": False, "insuranceStatus": "NOT_REQUIRED",
            "status": status, "submittedBy": str(op["_id"]), "submittedAt": now_iso, "updatedAt": now_iso
        }
        coll.insert_one(doc)

    resp = client.get('/api/admin/alerts')
    alerts = resp.get_json()["alerts"]
    fail_alerts = [a for a in alerts if a["type"] == "FAILURE_RATE_SPIKE"]
    assert len(fail_alerts) == 0  # 15.0% is NOT > 15%

    # Case B: Strictly > 15% (4 failed out of 20 total = 20%) -> ALERT TRIGGERED
    coll.update_one({"parcelId": "P-FAIL-3"}, {"$set": {"status": "FAILED"}})
    resp = client.get('/api/admin/alerts')
    alerts = resp.get_json()["alerts"]
    fail_alerts = [a for a in alerts if a["type"] == "FAILURE_RATE_SPIKE"]
    assert len(fail_alerts) == 1
    assert fail_alerts[0]["severity"] == "HIGH"
    assert fail_alerts[0]["currentValue"] == 20.0

def test_admin_alerts_volume_spike(client):
    helper_register_and_login(client, "admin1", "admin")
    op = UserModel.find_by_username("admin1")
    coll = ParcelModel.get_collection()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    baseline_time = (now - timedelta(hours=5)).isoformat()

    # Baseline 24h volume: 24 total over 24 hours -> 1.0 parcel/hr baseline.
    # 2x baseline = 2.0 parcels/hr.
    for i in range(24):
        coll.insert_one({
            "parcelId": f"P-BASE-{i}", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2",
            "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10.0,
            "status": "RECEIVED", "submittedBy": str(op["_id"]), "submittedAt": baseline_time, "updatedAt": baseline_time
        })

    # Last hour volume: exactly 2 parcels -> volume exactly 2x baseline -> NO ALERT
    for i in range(2):
        coll.insert_one({
            "parcelId": f"P-NOW-{i}", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2",
            "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10.0,
            "status": "RECEIVED", "submittedBy": str(op["_id"]), "submittedAt": now_iso, "updatedAt": now_iso
        })

    resp = client.get('/api/admin/alerts')
    vol_alerts = [a for a in resp.get_json()["alerts"] if a["type"] == "VOLUME_SPIKE"]
    assert len(vol_alerts) == 0

    # Add 1 more parcel to last hour -> 3 parcels > 2.0 baseline -> ALERT TRIGGERED
    coll.insert_one({
        "parcelId": "P-NOW-3", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2",
        "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10.0,
        "status": "RECEIVED", "submittedBy": str(op["_id"]), "submittedAt": now_iso, "updatedAt": now_iso
    })
    resp = client.get('/api/admin/alerts')
    vol_alerts = [a for a in resp.get_json()["alerts"] if a["type"] == "VOLUME_SPIKE"]
    assert len(vol_alerts) == 1
    assert vol_alerts[0]["currentValue"] == 3

def test_admin_alerts_department_skew(client):
    helper_register_and_login(client, "admin1", "admin")
    op = UserModel.find_by_username("admin1")
    coll = ParcelModel.get_collection()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Case A: 4 parcels total (fewer than 5) with 100% MAIL -> NO ALERT (<5 total parcels)
    for i in range(4):
        coll.insert_one({
            "parcelId": f"P-SKEW-{i}", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2",
            "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10.0,
            "department": "MAIL", "status": "ROUTING_EVALUATED", "submittedBy": str(op["_id"]),
            "submittedAt": now_iso, "updatedAt": now_iso
        })

    resp = client.get('/api/admin/alerts')
    skew_alerts = [a for a in resp.get_json()["alerts"] if a["type"] == "DEPARTMENT_SKEW"]
    assert len(skew_alerts) == 0

    # Case B: Exactly 5 total parcels, 4 MAIL, 1 REGULAR -> MAIL = 80.0% -> NO ALERT (exactly 80%)
    coll.insert_one({
        "parcelId": "P-SKEW-4", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2",
        "origin": "X", "destination": "Y", "weightKg": 2.0, "valueEur": 10.0,
        "department": "REGULAR", "status": "ROUTING_EVALUATED", "submittedBy": str(op["_id"]),
        "submittedAt": now_iso, "updatedAt": now_iso
    })
    resp = client.get('/api/admin/alerts')
    skew_alerts = [a for a in resp.get_json()["alerts"] if a["type"] == "DEPARTMENT_SKEW"]
    assert len(skew_alerts) == 0

    # Case C: Add 6th parcel as MAIL -> MAIL = 5/6 = 83.33% > 80.0% -> ALERT TRIGGERED
    coll.insert_one({
        "parcelId": "P-SKEW-5", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2",
        "origin": "X", "destination": "Y", "weightKg": 0.5, "valueEur": 10.0,
        "department": "MAIL", "status": "ROUTING_EVALUATED", "submittedBy": str(op["_id"]),
        "submittedAt": now_iso, "updatedAt": now_iso
    })
    resp = client.get('/api/admin/alerts')
    skew_alerts = [a for a in resp.get_json()["alerts"] if a["type"] == "DEPARTMENT_SKEW"]
    assert len(skew_alerts) == 1
    assert skew_alerts[0]["department"] == "MAIL"

def test_admin_alerts_insurance_spike(client):
    helper_register_and_login(client, "admin1", "admin")
    op = UserModel.find_by_username("admin1")
    coll = ParcelModel.get_collection()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    baseline_time = (now - timedelta(hours=5)).isoformat()

    # Baseline 24h: 24 insurance-required parcels -> 1.0/hr baseline
    for i in range(24):
        coll.insert_one({
            "parcelId": f"P-INS-BASE-{i}", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2",
            "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 1500.0,
            "insuranceRequired": True, "status": "AWAITING_INSURANCE", "submittedBy": str(op["_id"]),
            "submittedAt": baseline_time, "updatedAt": baseline_time
        })

    # Last hour: 2 insurance parcels -> volume exactly 2x baseline -> NO ALERT
    for i in range(2):
        coll.insert_one({
            "parcelId": f"P-INS-NOW-{i}", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2",
            "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 1500.0,
            "insuranceRequired": True, "status": "AWAITING_INSURANCE", "submittedBy": str(op["_id"]),
            "submittedAt": now_iso, "updatedAt": now_iso
        })

    resp = client.get('/api/admin/alerts')
    ins_alerts = [a for a in resp.get_json()["alerts"] if a["type"] == "INSURANCE_SPIKE"]
    assert len(ins_alerts) == 0

    # Add 3rd insurance parcel to last hour -> 3 > 2.0 baseline -> ALERT TRIGGERED
    coll.insert_one({
        "parcelId": "P-INS-NOW-2", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2",
        "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 1500.0,
        "insuranceRequired": True, "status": "AWAITING_INSURANCE", "submittedBy": str(op["_id"]),
        "submittedAt": now_iso, "updatedAt": now_iso
    })
    resp = client.get('/api/admin/alerts')
    ins_alerts = [a for a in resp.get_json()["alerts"] if a["type"] == "INSURANCE_SPIKE"]
    assert len(ins_alerts) == 1
    assert ins_alerts[0]["currentValue"] == 3
