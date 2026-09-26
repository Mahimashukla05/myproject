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
    dummy = DummyCollection()
    monkeypatch.setattr("models.user_model.UserModel.get_collection", lambda: dummy)
    from services.auth_service import _failed_login_attempts
    _failed_login_attempts.clear()

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    with app.test_client() as client:
        yield client

def test_1_valid_registration(client):
    res = client.post('/api/auth/register', json={
        "fullName": "John Doe",
        "username": "johndoe",
        "email": "john@example.com",
        "mobile": "9876543210",
        "password": "Password123!",
        "confirmPassword": "Password123!",
        "role": "user"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["username"] == "johndoe"
    assert data["user"]["role"] == "user"

def test_2_duplicate_username(client):
    client.post('/api/auth/register', json={
        "fullName": "User One", "username": "uniqueuser", "email": "user1@example.com",
        "mobile": "9876543211", "password": "Password123!", "confirmPassword": "Password123!"
    })
    res = client.post('/api/auth/register', json={
        "fullName": "User Two", "username": "uniqueuser", "email": "user2@example.com",
        "mobile": "9876543212", "password": "Password123!", "confirmPassword": "Password123!"
    })
    assert res.status_code == 400
    assert "Username is already taken" in res.get_json()["error"]

def test_3_duplicate_email(client):
    client.post('/api/auth/register', json={
        "fullName": "User One", "username": "userone", "email": "sameemail@example.com",
        "mobile": "9876543213", "password": "Password123!", "confirmPassword": "Password123!"
    })
    res = client.post('/api/auth/register', json={
        "fullName": "User Two", "username": "usertwo", "email": "sameemail@example.com",
        "mobile": "9876543214", "password": "Password123!", "confirmPassword": "Password123!"
    })
    assert res.status_code == 400
    assert "Email address is already registered" in res.get_json()["error"]

def test_4_valid_login(client):
    client.post('/api/auth/register', json={
        "fullName": "Login User", "username": "loginuser", "email": "login@example.com",
        "mobile": "9876543215", "password": "Password123!", "confirmPassword": "Password123!"
    })
    res = client.post('/api/auth/login', json={
        "identifier": "loginuser",
        "password": "Password123!"
    })
    assert res.status_code == 200
    assert res.get_json()["success"] is True

def test_5_invalid_password(client):
    client.post('/api/auth/register', json={
        "fullName": "Pass User", "username": "passuser", "email": "pass@example.com",
        "mobile": "9876543216", "password": "Password123!", "confirmPassword": "Password123!"
    })
    res = client.post('/api/auth/login', json={
        "identifier": "passuser",
        "password": "WrongPassword!"
    })
    assert res.status_code == 401
    assert "Invalid username" in res.get_json()["error"]

def test_6_invalid_credentials(client):
    res = client.post('/api/auth/login', json={
        "identifier": "nonexistentuser",
        "password": "Password123!"
    })
    assert res.status_code == 401
    assert "Invalid username" in res.get_json()["error"]

def test_7_logout(client):
    client.post('/api/auth/register', json={
        "fullName": "Logout User", "username": "logoutuser", "email": "logout@example.com",
        "mobile": "9876543217", "password": "Password123!", "confirmPassword": "Password123!"
    })
    login_res = client.post('/api/auth/login', json={"identifier": "logoutuser", "password": "Password123!"})
    csrf_token = login_res.get_json()["csrfToken"]
    res = client.post('/api/auth/logout', headers={"X-CSRF-Token": csrf_token})
    assert res.status_code == 200
    assert res.get_json()["success"] is True

def test_8_authenticated_endpoint(client):
    client.post('/api/auth/register', json={
        "fullName": "Me User", "username": "meuser", "email": "me@example.com",
        "mobile": "9876543218", "password": "Password123!", "confirmPassword": "Password123!"
    })
    client.post('/api/auth/login', json={"identifier": "meuser", "password": "Password123!"})
    res = client.get('/api/auth/me')
    assert res.status_code == 200
    assert res.get_json()["user"]["username"] == "meuser"

def test_9_unauthenticated_endpoint_returns_401(client):
    res = client.get('/api/auth/me')
    assert res.status_code == 401
    assert "Authentication required" in res.get_json()["error"]

def test_10_wrong_role_returns_403(client):
    client.post('/api/auth/register', json={
        "fullName": "Normal User", "username": "normaluser", "email": "normal@example.com",
        "mobile": "9876543219", "password": "Password123!", "confirmPassword": "Password123!",
        "role": "user"
    })
    client.post('/api/auth/login', json={"identifier": "normaluser", "password": "Password123!"})
    res = client.get('/api/admin/users')
    assert res.status_code == 403
    assert "Access denied" in res.get_json()["error"]

def test_11_admin_access_allowed(client):
    client.post('/api/auth/register', json={
        "fullName": "Admin User", "username": "adminuser", "email": "admin@example.com",
        "mobile": "9876543220", "password": "Password123!", "confirmPassword": "Password123!",
        "role": "admin", "adminKey": Config.ADMIN_REGISTRATION_KEY
    })
    client.post('/api/auth/login', json={"identifier": "adminuser", "password": "Password123!"})
    res = client.get('/api/admin/users')
    assert res.status_code == 200
    assert res.get_json()["success"] is True

def test_12_operator_access_denied_from_admin_endpoint(client):
    client.post('/api/auth/register', json={
        "fullName": "Operator User", "username": "opuser", "email": "op@example.com",
        "mobile": "9876543221", "password": "Password123!", "confirmPassword": "Password123!",
        "role": "operator"
    })
    client.post('/api/auth/login', json={"identifier": "opuser", "password": "Password123!"})
    res = client.get('/api/admin/users')
    assert res.status_code == 403
    assert "Access denied" in res.get_json()["error"]

def test_13_normal_user_access_denied_from_admin_endpoint(client):
    client.post('/api/auth/register', json={
        "fullName": "Basic User", "username": "basicuser", "email": "basic@example.com",
        "mobile": "9876543222", "password": "Password123!", "confirmPassword": "Password123!"
    })
    client.post('/api/auth/login', json={"identifier": "basicuser", "password": "Password123!"})
    res = client.get('/api/admin/users')
    assert res.status_code == 403
    assert "Access denied" in res.get_json()["error"]
