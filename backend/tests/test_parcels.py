import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config.settings import Config

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

    def find(self, query, projection=None):
        res = []
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
    
    def mock_get_col(cls):
        if cls.COLLECTION_NAME == "users":
            return user_dummy
        return parcel_dummy

    monkeypatch.setattr("models.user_model.UserModel.get_collection", classmethod(lambda cls: user_dummy))
    monkeypatch.setattr("models.parcel_model.ParcelModel.get_collection", classmethod(lambda cls: parcel_dummy))
    
    from services.auth_service import _failed_login_attempts
    _failed_login_attempts.clear()

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-parcel-secret'
    with app.test_client() as client:
        yield client

def helper_register_and_login(client, username, role="operator", admin_key=""):
    payload = {
        "fullName": f"Test {username}",
        "username": username,
        "email": f"{username}@example.com",
        "mobile": "9876543210",
        "password": "Password123!",
        "confirmPassword": "Password123!",
        "role": role
    }
    if role == "admin":
        payload["adminKey"] = admin_key or Config.ADMIN_REGISTRATION_KEY

    client.post('/api/auth/register', json=payload)
    login_res = client.post('/api/auth/login', json={"identifier": username, "password": "Password123!"})
    return login_res.get_json()["csrfToken"]

def test_parcel_1_valid_parcel_creation_by_operator(client):
    csrf_token = helper_register_and_login(client, "op_valid", role="operator")
    
    res = client.post('/api/parcels', json={
        "senderName": "Alice Smith",
        "senderContact": "+1234567890",
        "receiverName": "Bob Jones",
        "receiverContact": "+9876543210",
        "origin": "Berlin",
        "destination": "Munich",
        "weightKg": 2.5,
        "valueEur": 150.00
    }, headers={"X-CSRF-Token": csrf_token})

    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    parcel = data["parcel"]
    assert parcel["parcelId"].startswith("PCL-")
    assert parcel["senderName"] == "Alice Smith"
    assert parcel["status"] == "RECEIVED"
    assert parcel["department"] is None
    assert parcel["insuranceRequired"] is False
    assert parcel["insuranceStatus"] == "NOT_REQUIRED"
    assert parcel["failureReason"] is None

def test_parcel_2_missing_required_field(client):
    csrf_token = helper_register_and_login(client, "op_missing", role="operator")
    
    res = client.post('/api/parcels', json={
        "senderName": "Alice Smith",
        # senderContact missing
        "receiverName": "Bob Jones",
        "receiverContact": "+9876543210",
        "origin": "Berlin",
        "destination": "Munich",
        "weightKg": 2.5,
        "valueEur": 150.00
    }, headers={"X-CSRF-Token": csrf_token})

    assert res.status_code == 400
    assert "Missing required fields" in res.get_json()["error"]

def test_parcel_3_invalid_weight_zero_or_negative(client):
    csrf_token = helper_register_and_login(client, "op_weight", role="operator")
    
    # Weight <= 0
    res = client.post('/api/parcels', json={
        "senderName": "Alice", "senderContact": "123", "receiverName": "Bob", "receiverContact": "456",
        "origin": "Berlin", "destination": "Munich", "weightKg": 0, "valueEur": 10
    }, headers={"X-CSRF-Token": csrf_token})
    assert res.status_code == 400
    assert "must be greater than 0.0" in res.get_json()["error"]

def test_parcel_4_negative_value_eur(client):
    csrf_token = helper_register_and_login(client, "op_value", role="operator")
    
    res = client.post('/api/parcels', json={
        "senderName": "Alice", "senderContact": "123", "receiverName": "Bob", "receiverContact": "456",
        "origin": "Berlin", "destination": "Munich", "weightKg": 1.5, "valueEur": -5.0
    }, headers={"X-CSRF-Token": csrf_token})
    assert res.status_code == 400
    assert "must be non-negative" in res.get_json()["error"]

def test_parcel_5_invalid_data_type_string_weight(client):
    csrf_token = helper_register_and_login(client, "op_type", role="operator")
    
    res = client.post('/api/parcels', json={
        "senderName": "Alice", "senderContact": "123", "receiverName": "Bob", "receiverContact": "456",
        "origin": "Berlin", "destination": "Munich", "weightKg": "heavy", "valueEur": 10
    }, headers={"X-CSRF-Token": csrf_token})
    assert res.status_code == 400
    assert "must be a numeric value" in res.get_json()["error"]

def test_parcel_6_malformed_nested_json_object(client):
    csrf_token = helper_register_and_login(client, "op_json", role="operator")
    
    res = client.post('/api/parcels', json={
        "senderName": {"$ne": None}, "senderContact": "123", "receiverName": "Bob", "receiverContact": "456",
        "origin": "Berlin", "destination": "Munich", "weightKg": 1.5, "valueEur": 10
    }, headers={"X-CSRF-Token": csrf_token})
    assert res.status_code == 400
    assert "must be a string" in res.get_json()["error"]

def test_parcel_7_unauthenticated_request_returns_401(client):
    res = client.post('/api/parcels', json={
        "senderName": "Alice", "senderContact": "123", "receiverName": "Bob", "receiverContact": "456",
        "origin": "Berlin", "destination": "Munich", "weightKg": 1.5, "valueEur": 10
    })
    assert res.status_code == 401

def test_parcel_8_normal_user_registration_rejected(client):
    res = client.post('/api/auth/register', json={
        "fullName": "Normal User", "username": "normal_user_parcel", "email": "normal_parcel@example.com",
        "mobile": "9876543999", "password": "Password123!", "confirmPassword": "Password123!",
        "role": "user"
    })
    assert res.status_code == 400
    assert "Allowed roles are 'operator' and 'admin'." in res.get_json()["error"]

def test_parcel_9_admin_can_create_parcel(client):
    csrf_token = helper_register_and_login(client, "admin_parcel", role="admin")
    
    res = client.post('/api/parcels', json={
        "senderName": "Admin Sender", "senderContact": "123", "receiverName": "Bob", "receiverContact": "456",
        "origin": "Berlin", "destination": "Munich", "weightKg": 5.0, "valueEur": 200
    }, headers={"X-CSRF-Token": csrf_token})
    assert res.status_code == 201

def test_parcel_10_unique_parcel_id_generation(client):
    csrf_token = helper_register_and_login(client, "op_unique", role="operator")
    
    res1 = client.post('/api/parcels', json={
        "senderName": "Sender One", "senderContact": "123", "receiverName": "Bob", "receiverContact": "456",
        "origin": "Berlin", "destination": "Munich", "weightKg": 1.0, "valueEur": 50
    }, headers={"X-CSRF-Token": csrf_token})
    
    res2 = client.post('/api/parcels', json={
        "senderName": "Sender Two", "senderContact": "123", "receiverName": "Bob", "receiverContact": "456",
        "origin": "Berlin", "destination": "Munich", "weightKg": 2.0, "valueEur": 75
    }, headers={"X-CSRF-Token": csrf_token})

    id1 = res1.get_json()["parcel"]["parcelId"]
    id2 = res2.get_json()["parcel"]["parcelId"]
    assert id1 != id2

def test_parcel_11_submitted_by_uses_session_user_id_not_body(client):
    csrf_token = helper_register_and_login(client, "op_submitted", role="operator")
    
    res = client.post('/api/parcels', json={
        "senderName": "Sender", "senderContact": "123", "receiverName": "Bob", "receiverContact": "456",
        "origin": "Berlin", "destination": "Munich", "weightKg": 1.0, "valueEur": 50,
        "submittedBy": "fake_hacker_id_123"
    }, headers={"X-CSRF-Token": csrf_token})

    parcel = res.get_json()["parcel"]
    assert parcel["submittedBy"] != "fake_hacker_id_123"

def test_parcel_12_get_parcel_by_id_success(client):
    csrf_token = helper_register_and_login(client, "op_get", role="operator")
    
    create_res = client.post('/api/parcels', json={
        "senderName": "Get Sender", "senderContact": "123", "receiverName": "Bob", "receiverContact": "456",
        "origin": "Berlin", "destination": "Munich", "weightKg": 1.0, "valueEur": 50
    }, headers={"X-CSRF-Token": csrf_token})
    
    parcel_id = create_res.get_json()["parcel"]["parcelId"]

    get_res = client.get(f'/api/parcels/{parcel_id}')
    assert get_res.status_code == 200
    assert get_res.get_json()["parcel"]["parcelId"] == parcel_id

def test_parcel_13_get_nonexistent_parcel_returns_404(client):
    helper_register_and_login(client, "op_404", role="operator")
    
    res = client.get('/api/parcels/PCL-NONEXISTENT999')
    assert res.status_code == 404
    assert "not found" in res.get_json()["error"]

# --- 14. Strict Name, Origin & Destination Field Alphabet Rules ---
def test_strict_name_and_location_validation_rules(client):
    csrf_token = helper_register_and_login(client, "op_strict_val", role="operator")

    base_payload = {
        "senderName": "John Doe",
        "senderContact": "+91 9876543210",
        "receiverName": "Rahul Kumar",
        "receiverContact": "+91 9123456789",
        "origin": "New Delhi",
        "destination": "Mumbai",
        "weightKg": 2.5,
        "valueEur": 100.0
    }

    # 1. Valid payload succeeds
    res = client.post('/api/parcels', json=base_payload, headers={"X-CSRF-Token": csrf_token})
    assert res.status_code == 201

    # 2. Invalid senderName with numbers
    bad_sender = dict(base_payload, senderName="John123")
    res = client.post('/api/parcels', json=bad_sender, headers={"X-CSRF-Token": csrf_token})
    assert res.status_code == 400
    assert "must contain only English alphabets and spaces" in res.get_json()["error"]

    # 3. Invalid receiverName with hyphen
    bad_receiver = dict(base_payload, receiverName="John-Doe")
    res = client.post('/api/parcels', json=bad_receiver, headers={"X-CSRF-Token": csrf_token})
    assert res.status_code == 400
    assert "must contain only English alphabets and spaces" in res.get_json()["error"]

    # 4. Invalid origin with numbers
    bad_origin = dict(base_payload, origin="Raipur123")
    res = client.post('/api/parcels', json=bad_origin, headers={"X-CSRF-Token": csrf_token})
    assert res.status_code == 400
    assert "must contain only English alphabets and spaces" in res.get_json()["error"]

    # 5. Invalid destination with special symbol
    bad_dest = dict(base_payload, destination="Delhi@India")
    res = client.post('/api/parcels', json=bad_dest, headers={"X-CSRF-Token": csrf_token})
    assert res.status_code == 400
    assert "must contain only English alphabets and spaces" in res.get_json()["error"]
