import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config.settings import Config
from services.routing_service import RoutingService

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

    monkeypatch.setattr("models.user_model.UserModel.get_collection", classmethod(lambda cls: user_dummy))
    monkeypatch.setattr("models.parcel_model.ParcelModel.get_collection", classmethod(lambda cls: parcel_dummy))

    from services.auth_service import _failed_login_attempts
    _failed_login_attempts.clear()

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-routing-secret'
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

# --- 1. Mandatory Unit Boundary Tests ---

def test_routing_boundary_1_00_kg_mail():
    res = RoutingService.evaluate_routing(1.00, 500)
    assert res["department"] == "MAIL"

def test_routing_boundary_1_01_kg_regular():
    res = RoutingService.evaluate_routing(1.01, 500)
    assert res["department"] == "REGULAR"

def test_routing_boundary_10_00_kg_regular():
    res = RoutingService.evaluate_routing(10.00, 500)
    assert res["department"] == "REGULAR"

def test_routing_boundary_10_01_kg_heavy():
    res = RoutingService.evaluate_routing(10.01, 500)
    assert res["department"] == "HEAVY"

def test_insurance_boundary_1000_00_not_required():
    res = RoutingService.evaluate_routing(5.00, 1000.00)
    assert res["insuranceRequired"] is False
    assert res["insuranceStatus"] == "NOT_REQUIRED"
    assert res["status"] == "ROUTING_EVALUATED"

def test_insurance_boundary_1000_01_required():
    res = RoutingService.evaluate_routing(5.00, 1000.01)
    assert res["insuranceRequired"] is True
    assert res["insuranceStatus"] == "PENDING"
    assert res["status"] == "AWAITING_INSURANCE"

def test_combination_2kg_1500eur():
    res = RoutingService.evaluate_routing(2.0, 1500.0)
    assert res["department"] == "REGULAR"
    assert res["insuranceRequired"] is True
    assert res["insuranceStatus"] == "PENDING"
    assert res["status"] == "AWAITING_INSURANCE"

def test_combination_2kg_500eur():
    res = RoutingService.evaluate_routing(2.0, 500.0)
    assert res["department"] == "REGULAR"
    assert res["insuranceRequired"] is False
    assert res["insuranceStatus"] == "NOT_REQUIRED"
    assert res["status"] == "ROUTING_EVALUATED"

# --- 2. API & Authorization Integration Tests ---

def test_api_route_parcel_operator_success(client):
    csrf_token = helper_register_and_login(client, "op_route", role="operator")
    
    create_res = client.post('/api/parcels', json={
        "senderName": "Alice", "senderContact": "123", "receiverName": "Bob", "receiverContact": "456",
        "origin": "Berlin", "destination": "Munich", "weightKg": 2.0, "valueEur": 1500.0
    }, headers={"X-CSRF-Token": csrf_token})
    parcel_id = create_res.get_json()["parcel"]["parcelId"]

    route_res = client.post(f'/api/parcels/{parcel_id}/route', headers={"X-CSRF-Token": csrf_token})
    assert route_res.status_code == 200
    p = route_res.get_json()["parcel"]
    assert p["department"] == "REGULAR"
    assert p["insuranceRequired"] is True
    assert p["insuranceStatus"] == "PENDING"
    assert p["status"] == "AWAITING_INSURANCE"

def test_api_route_parcel_admin_success(client):
    csrf_token = helper_register_and_login(client, "admin_route", role="admin")
    
    create_res = client.post('/api/parcels', json={
        "senderName": "Alice", "senderContact": "123", "receiverName": "Bob", "receiverContact": "456",
        "origin": "Berlin", "destination": "Munich", "weightKg": 0.5, "valueEur": 500.0
    }, headers={"X-CSRF-Token": csrf_token})
    parcel_id = create_res.get_json()["parcel"]["parcelId"]

    route_res = client.post(f'/api/parcels/{parcel_id}/route', headers={"X-CSRF-Token": csrf_token})
    assert route_res.status_code == 200
    p = route_res.get_json()["parcel"]
    assert p["department"] == "MAIL"
    assert p["insuranceRequired"] is False
    assert p["status"] == "ROUTING_EVALUATED"

def test_api_route_parcel_normal_user_registration_rejected(client):
    res = client.post('/api/auth/register', json={
        "fullName": "Normal Route User", "username": "normal_route_user", "email": "route_user@example.com",
        "mobile": "9944332211", "password": "Password123!", "confirmPassword": "Password123!",
        "role": "user"
    })
    assert res.status_code == 400
    assert "Allowed roles are 'operator' and 'admin'." in res.get_json()["error"]

def test_api_route_parcel_unauthenticated_401(client):
    res = client.post('/api/parcels/PCL-SOMEID/route')
    assert res.status_code == 401

def test_api_route_nonexistent_parcel_404(client):
    csrf_token = helper_register_and_login(client, "op_404_route", role="operator")
    res = client.post('/api/parcels/PCL-DOESNOTEXIST/route', headers={"X-CSRF-Token": csrf_token})
    assert res.status_code == 404
    assert "not found" in res.get_json()["error"]

def test_api_route_ignores_client_request_body_override(client):
    csrf_token = helper_register_and_login(client, "op_override", role="operator")
    
    create_res = client.post('/api/parcels', json={
        "senderName": "Alice", "senderContact": "123", "receiverName": "Bob", "receiverContact": "456",
        "origin": "Berlin", "destination": "Munich", "weightKg": 0.5, "valueEur": 100.0
    }, headers={"X-CSRF-Token": csrf_token})
    parcel_id = create_res.get_json()["parcel"]["parcelId"]

    route_res = client.post(f'/api/parcels/{parcel_id}/route', json={
        "weightKg": 50.0,
        "valueEur": 9999.0,
        "department": "HEAVY",
        "insuranceRequired": True
    }, headers={"X-CSRF-Token": csrf_token})

    assert route_res.status_code == 200
    p = route_res.get_json()["parcel"]
    assert p["department"] == "MAIL"
    assert p["insuranceRequired"] is False

def test_idempotent_repeated_routing(client):
    csrf_token = helper_register_and_login(client, "op_repeat", role="operator")
    
    create_res = client.post('/api/parcels', json={
        "senderName": "Alice", "senderContact": "123", "receiverName": "Bob", "receiverContact": "456",
        "origin": "Berlin", "destination": "Munich", "weightKg": 15.0, "valueEur": 500.0
    }, headers={"X-CSRF-Token": csrf_token})
    parcel_id = create_res.get_json()["parcel"]["parcelId"]

    res1 = client.post(f'/api/parcels/{parcel_id}/route', headers={"X-CSRF-Token": csrf_token})
    assert res1.status_code == 200
    p1 = res1.get_json()["parcel"]

    res2 = client.post(f'/api/parcels/{parcel_id}/route', headers={"X-CSRF-Token": csrf_token})
    assert res2.status_code == 200
    p2 = res2.get_json()["parcel"]

    assert p1["parcelId"] == p2["parcelId"]
    assert p2["department"] == "HEAVY"
    assert p2["insuranceRequired"] is False
