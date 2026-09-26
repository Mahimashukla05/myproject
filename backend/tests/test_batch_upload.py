import pytest
import io
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config.settings import Config
from models.parcel_model import ParcelModel

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

    monkeypatch.setattr("models.user_model.UserModel.get_collection", classmethod(lambda cls: user_dummy))
    monkeypatch.setattr("models.parcel_model.ParcelModel.get_collection", classmethod(lambda cls: parcel_dummy))
    monkeypatch.setattr("models.audit_model.AuditModel.get_collection", classmethod(lambda cls: audit_dummy))
    monkeypatch.setattr("config.db.Database.get_db", staticmethod(lambda: {"users": user_dummy, "parcels": parcel_dummy, "audit_logs": audit_dummy}))

    from services.auth_service import _failed_login_attempts
    _failed_login_attempts.clear()

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-batch-secret'
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

# --- 1. Valid JSON Batch ---
def test_valid_json_batch(client):
    csrf = helper_register_and_login(client, "op_json_batch", role="operator")
    json_data = {
        "parcels": [
            {
                "parcelId": "PCL-JSON-001",
                "senderName": "Alice", "senderContact": "9876543210",
                "receiverName": "Bob", "receiverContact": "9876543211",
                "origin": "Raipur", "destination": "Delhi",
                "weightKg": 2.5, "valueEur": 500
            },
            {
                "parcelId": "PCL-JSON-002",
                "senderName": "Charlie", "senderContact": "9876543212",
                "receiverName": "David", "receiverContact": "9876543213",
                "origin": "Mumbai", "destination": "Pune",
                "weightKg": 12.0, "valueEur": 1500
            }
        ]
    }
    data = {'file': (io.BytesIO(json.dumps(json_data).encode('utf-8')), 'batch.json')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})

    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert body["total"] == 2
    assert body["successful"] == 2
    assert body["failed"] == 0

# --- 2. Valid XML Batch ---
def test_valid_xml_batch(client):
    csrf = helper_register_and_login(client, "op_xml_batch", role="operator")
    xml_content = """<parcels>
        <parcel>
            <parcelId>PCL-XML-001</parcelId>
            <senderName>Alice</senderName>
            <senderContact>9876543210</senderContact>
            <receiverName>Bob</receiverName>
            <receiverContact>9876543211</receiverContact>
            <origin>Raipur</origin>
            <destination>Delhi</destination>
            <weightKg>2.5</weightKg>
            <valueEur>500</valueEur>
        </parcel>
        <parcel>
            <parcelId>PCL-XML-002</parcelId>
            <senderName>Charlie</senderName>
            <senderContact>9876543212</senderContact>
            <receiverName>David</receiverName>
            <receiverContact>9876543213</receiverContact>
            <origin>Mumbai</origin>
            <destination>Pune</destination>
            <weightKg>0.5</weightKg>
            <valueEur>50</valueEur>
        </parcel>
    </parcels>"""
    data = {'file': (io.BytesIO(xml_content.encode('utf-8')), 'batch.xml')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})

    assert res.status_code == 200
    body = res.get_json()
    assert body["total"] == 2
    assert body["successful"] == 2
    assert body["failed"] == 0

# --- 3. Malformed JSON ---
def test_malformed_json(client):
    csrf = helper_register_and_login(client, "op_bad_json", role="operator")
    data = {'file': (io.BytesIO(b"{ invalid json string"), 'batch.json')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 400
    assert "Malformed JSON" in res.get_json()["error"]

# --- 4. Malformed XML ---
def test_malformed_xml(client):
    csrf = helper_register_and_login(client, "op_bad_xml", role="operator")
    data = {'file': (io.BytesIO(b"<parcels><parcel>unclosed tag</parcels>"), 'batch.xml')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 400
    assert "Malformed XML" in res.get_json()["error"]

# --- 5. Missing File ---
def test_missing_file(client):
    csrf = helper_register_and_login(client, "op_no_file", role="operator")
    res = client.post('/api/parcels/batch', data={}, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 400
    assert "No file parameter" in res.get_json()["error"]

# --- 6. Empty File ---
def test_empty_file(client):
    csrf = helper_register_and_login(client, "op_empty_file", role="operator")
    data = {'file': (io.BytesIO(b""), 'empty.json')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 400
    assert "file is empty" in res.get_json()["error"].lower()

# --- 7. Unsupported Extension ---
def test_unsupported_extension(client):
    csrf = helper_register_and_login(client, "op_unsupported_ext", role="operator")
    data = {'file': (io.BytesIO(b"some content"), 'batch.txt')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 400
    assert "Unsupported file extension" in res.get_json()["error"]

# --- 8. Unsupported MIME / Content Type ---
def test_unsupported_mime_type(client):
    csrf = helper_register_and_login(client, "op_bad_mime", role="operator")
    data = {'file': (io.BytesIO(b"content"), 'batch.json', 'image/png')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 400
    assert "Unsupported MIME type" in res.get_json()["error"]

# --- 9. Oversized File ---
def test_oversized_file(client, monkeypatch):
    csrf = helper_register_and_login(client, "op_large_file", role="operator")
    monkeypatch.setattr(Config, "MAX_BATCH_FILE_SIZE_BYTES", 100) # Small 100 byte limit
    large_payload = json.dumps({"parcels": [{"parcelId": "P1"*100}]}).encode('utf-8')
    data = {'file': (io.BytesIO(large_payload), 'batch.json')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 413
    assert "exceeds maximum allowed limit" in res.get_json()["error"]

# --- 10. Missing Required Parcel Field ---
def test_missing_required_parcel_field(client):
    csrf = helper_register_and_login(client, "op_missing_field", role="operator")
    json_data = {
        "parcels": [
            {
                "parcelId": "PCL-MISS-01",
                "senderName": "Alice", "senderContact": "9876543210",
                "receiverName": "Bob", "receiverContact": "9876543211",
                "origin": "Raipur",
                # destination missing!
                "weightKg": 2.5, "valueEur": 500
            }
        ]
    }
    data = {'file': (io.BytesIO(json.dumps(json_data).encode('utf-8')), 'batch.json')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    body = res.get_json()
    assert body["failed"] == 1
    assert body["results"][0]["status"] == "FAILED"
    assert any("destination" in err for err in body["results"][0]["errors"])

# --- 11. Invalid Weight ---
def test_invalid_weight(client):
    csrf = helper_register_and_login(client, "op_inv_weight", role="operator")
    json_data = {
        "parcels": [
            {
                "parcelId": "PCL-WGT-01",
                "senderName": "A", "senderContact": "123", "receiverName": "B", "receiverContact": "456",
                "origin": "A", "destination": "B",
                "weightKg": -5.0, "valueEur": 100
            }
        ]
    }
    data = {'file': (io.BytesIO(json.dumps(json_data).encode('utf-8')), 'batch.json')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})
    body = res.get_json()
    assert body["failed"] == 1
    assert any("weightKg" in err for err in body["results"][0]["errors"])

# --- 12. Invalid Value ---
def test_invalid_value(client):
    csrf = helper_register_and_login(client, "op_inv_val", role="operator")
    json_data = {
        "parcels": [
            {
                "parcelId": "PCL-VAL-01",
                "senderName": "A", "senderContact": "123", "receiverName": "B", "receiverContact": "456",
                "origin": "A", "destination": "B",
                "weightKg": 1.0, "valueEur": -50.0
            }
        ]
    }
    data = {'file': (io.BytesIO(json.dumps(json_data).encode('utf-8')), 'batch.json')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})
    body = res.get_json()
    assert body["failed"] == 1
    assert any("valueEur" in err for err in body["results"][0]["errors"])

# --- 13. Invalid Parcel Structure ---
def test_invalid_parcel_structure(client):
    csrf = helper_register_and_login(client, "op_struct", role="operator")
    json_data = {
        "parcels": ["not a dict parcel object"]
    }
    data = {'file': (io.BytesIO(json.dumps(json_data).encode('utf-8')), 'batch.json')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})
    body = res.get_json()
    assert body["failed"] == 1
    assert body["results"][0]["status"] == "FAILED"
    assert "Invalid row structure" in body["results"][0]["errors"][0]

# --- 14. Duplicate Parcel IDs Inside Same Batch ---
def test_duplicate_parcel_ids_inside_same_batch(client):
    csrf = helper_register_and_login(client, "op_dup_batch", role="operator")
    json_data = {
        "parcels": [
            {
                "parcelId": "PCL-DUP-INTRA",
                "senderName": "A", "senderContact": "123", "receiverName": "B", "receiverContact": "456",
                "origin": "A", "destination": "B", "weightKg": 1.0, "valueEur": 100
            },
            {
                "parcelId": "PCL-DUP-INTRA",
                "senderName": "A2", "senderContact": "123", "receiverName": "B2", "receiverContact": "456",
                "origin": "A", "destination": "B", "weightKg": 2.0, "valueEur": 200
            }
        ]
    }
    data = {'file': (io.BytesIO(json.dumps(json_data).encode('utf-8')), 'batch.json')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})
    body = res.get_json()
    assert body["total"] == 2
    assert body["successful"] == 1
    assert body["failed"] == 1
    assert body["results"][0]["status"] == "SUCCESS"
    assert body["results"][1]["status"] == "FAILED"
    assert "Duplicate parcelId" in body["results"][1]["errors"][0]

# --- 15. Parcel ID Already Existing in DB ---
def test_parcel_id_already_existing_in_db(client):
    csrf = helper_register_and_login(client, "op_db_exist", role="operator")

    # Create parcel PCL-EXIST-01 beforehand
    ParcelModel.create_parcel({
        "parcelId": "PCL-EXIST-01",
        "senderName": "Ex", "senderContact": "1", "receiverName": "Ey", "receiverContact": "2",
        "origin": "O", "destination": "D", "weightKg": 1.0, "valueEur": 10.0, "submittedBy": "system"
    })

    json_data = {
        "parcels": [
            {
                "parcelId": "PCL-EXIST-01",
                "senderName": "A", "senderContact": "123", "receiverName": "B", "receiverContact": "456",
                "origin": "A", "destination": "B", "weightKg": 1.0, "valueEur": 100
            }
        ]
    }
    data = {'file': (io.BytesIO(json.dumps(json_data).encode('utf-8')), 'batch.json')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})
    body = res.get_json()
    assert body["failed"] == 1
    assert "already exists in database" in body["results"][0]["errors"][0]

# --- 16. Partial Success ---
def test_partial_success(client):
    csrf = helper_register_and_login(client, "op_partial", role="operator")
    json_data = {
        "parcels": [
            {"parcelId": "P001", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10},
            {"parcelId": "P002", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": -1.0, "valueEur": 10}, # Invalid weight
            {"parcelId": "P003", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 2.0, "valueEur": 20},
            {"parcelId": "P004", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "weightKg": 3.0, "valueEur": 30}, # Missing destination
            {"parcelId": "P005", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 4.0, "valueEur": 40}
        ]
    }
    data = {'file': (io.BytesIO(json.dumps(json_data).encode('utf-8')), 'batch.json')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    body = res.get_json()
    assert body["total"] == 5
    assert body["successful"] == 3
    assert body["failed"] == 2
    assert body["results"][0]["status"] == "SUCCESS"
    assert body["results"][1]["status"] == "FAILED"
    assert body["results"][2]["status"] == "SUCCESS"
    assert body["results"][3]["status"] == "FAILED"
    assert body["results"][4]["status"] == "SUCCESS"

# --- 17. All Rows Invalid ---
def test_all_rows_invalid(client):
    csrf = helper_register_and_login(client, "op_all_inv", role="operator")
    json_data = {
        "parcels": [
            {"parcelId": "P001", "weightKg": -1.0},
            {"parcelId": "P002", "valueEur": -100.0}
        ]
    }
    data = {'file': (io.BytesIO(json.dumps(json_data).encode('utf-8')), 'batch.json')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    body = res.get_json()
    assert body["total"] == 2
    assert body["successful"] == 0
    assert body["failed"] == 2

# --- 18. Admin Allowed ---
def test_admin_allowed(client):
    admin_csrf = helper_register_and_login(client, "admin_batch_user", role="admin")
    json_data = {
        "parcels": [
            {"parcelId": "PCL-ADM-01", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10}
        ]
    }
    data = {'file': (io.BytesIO(json.dumps(json_data).encode('utf-8')), 'batch.json')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 200

# --- 19. Operator Allowed ---
def test_operator_allowed(client):
    op_csrf = helper_register_and_login(client, "op_batch_user", role="operator")
    json_data = {
        "parcels": [
            {"parcelId": "PCL-OPR-01", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10}
        ]
    }
    data = {'file': (io.BytesIO(json.dumps(json_data).encode('utf-8')), 'batch.json')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": op_csrf})
    assert res.status_code == 200

# --- 20. Normal User Gets 403 ---
def test_normal_user_gets_403(client):
    user_csrf = helper_register_and_login(client, "normal_batch_user", role="user")
    json_data = {"parcels": []}
    data = {'file': (io.BytesIO(json.dumps(json_data).encode('utf-8')), 'batch.json')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": user_csrf})
    assert res.status_code == 403

# --- 21. Unauthenticated Gets 401 ---
def test_unauthenticated_gets_401(client):
    data = {'file': (io.BytesIO(b"{}"), 'batch.json')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data')
    assert res.status_code == 401

# --- 22. XXE External Entity Attack Blocked ---
def test_xxe_external_entity_attack_blocked(client):
    csrf = helper_register_and_login(client, "op_xxe_target", role="operator")
    xxe_payload = """<?xml version="1.0" encoding="ISO-8859-1"?>
    <!DOCTYPE foo [
      <!ELEMENT foo ANY >
      <!ENTITY xxe SYSTEM "file:///etc/passwd" >]>
    <parcels>
      <parcel>
        <parcelId>&xxe;</parcelId>
        <senderName>A</senderName>
        <senderContact>123</senderContact>
        <receiverName>B</receiverName>
        <receiverContact>456</receiverContact>
        <origin>X</origin>
        <destination>Y</destination>
        <weightKg>1.0</weightKg>
        <valueEur>10</valueEur>
      </parcel>
    </parcels>"""

    data = {'file': (io.BytesIO(xxe_payload.encode('utf-8')), 'xxe_attack.xml')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 400
    body = res.get_json()
    assert "Security Violation" in body["error"]
    assert "DOCTYPE" in body["error"] or "ENTITY" in body["error"]

# --- 23. Technical Database Failure Distinguished From Validation Failure ---
def test_technical_database_failure_distinguished_from_validation_failure(client, monkeypatch):
    csrf = helper_register_and_login(client, "op_tech_db_fail", role="operator")
    monkeypatch.setattr("config.db.Database.get_db", staticmethod(lambda: None)) # DB Offline

    json_data = {
        "parcels": [
            {"parcelId": "P001", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10}
        ]
    }
    data = {'file': (io.BytesIO(json.dumps(json_data).encode('utf-8')), 'batch.json')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 503
    body = res.get_json()
    assert body["errorType"] == "TECHNICAL"
    assert "Database is currently unavailable" in body["error"]

# --- 24. No Fake Data Generated ---
def test_no_fake_data_generated(client):
    csrf = helper_register_and_login(client, "op_no_fake", role="operator")
    all_parcels = ParcelModel.get_parcels()
    # Check that initial parcel count is only what tests created, no seeded fake demo data
    for p in all_parcels:
        assert not p["parcelId"].startswith("DEMO-")
        assert not p["senderName"].startswith("Fake")

# --- 25. Batch Upload Leaves Parcel In RECEIVED State Without Routing ---
def test_batch_upload_leaves_parcel_in_received_state(client):
    csrf = helper_register_and_login(client, "op_received_check", role="operator")
    json_data = {
        "parcels": [
            {
                "parcelId": "PCL-RECV-001",
                "senderName": "Alice", "senderContact": "9876543210",
                "receiverName": "Bob", "receiverContact": "9876543211",
                "origin": "Raipur", "destination": "Delhi",
                "weightKg": 15.0, "valueEur": 2500.0  # Would route to HEAVY / REQUIRED if routed
            }
        ]
    }
    data = {'file': (io.BytesIO(json.dumps(json_data).encode('utf-8')), 'batch.json')}
    res = client.post('/api/parcels/batch', data=data, content_type='multipart/form-data', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200

    # Retrieve created parcel directly from DB to verify initial state
    parcel = ParcelModel.find_by_parcel_id("PCL-RECV-001")
    assert parcel is not None
    assert parcel["status"] == "RECEIVED"
    assert parcel["department"] is None
    assert parcel["insuranceRequired"] is False
    assert parcel["insuranceStatus"] == "NOT_REQUIRED"

