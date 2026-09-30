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
        "username": "JohnDoe1@",
        "email": "john@example.com",
        "mobile": "9876543210",
        "password": "Password123!",
        "confirmPassword": "Password123!",
        "role": "operator"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["username"] == "JohnDoe1@"
    assert data["user"]["role"] == "operator"

def test_1b_user_role_registration_rejected(client):
    res = client.post('/api/auth/register', json={
        "fullName": "Normal User",
        "username": "NormalUser1@",
        "email": "rej@example.com",
        "mobile": "9876543299",
        "password": "Password123!",
        "confirmPassword": "Password123!",
        "role": "user"
    })
    assert res.status_code == 400
    assert "Allowed roles are 'operator' and 'admin'." in res.get_json()["error"]

def test_2_duplicate_username(client):
    client.post('/api/auth/register', json={
        "fullName": "User One", "username": "UniqueUser1@", "email": "user1@example.com",
        "mobile": "9876543211", "password": "Password123!", "confirmPassword": "Password123!"
    })
    res = client.post('/api/auth/register', json={
        "fullName": "User Two", "username": "UniqueUser1@", "email": "user2@example.com",
        "mobile": "9876543212", "password": "Password123!", "confirmPassword": "Password123!"
    })
    assert res.status_code == 400
    assert "Username is already taken" in res.get_json()["error"]

def test_3_duplicate_email(client):
    client.post('/api/auth/register', json={
        "fullName": "User One", "username": "UserOne1@", "email": "sameemail@example.com",
        "mobile": "9876543213", "password": "Password123!", "confirmPassword": "Password123!"
    })
    res = client.post('/api/auth/register', json={
        "fullName": "User Two", "username": "UserTwo1@", "email": "sameemail@example.com",
        "mobile": "9876543214", "password": "Password123!", "confirmPassword": "Password123!"
    })
    assert res.status_code == 400
    assert "Email address is already registered" in res.get_json()["error"]

def test_4_valid_login(client):
    client.post('/api/auth/register', json={
        "fullName": "Login User", "username": "LoginUser1@", "email": "login@example.com",
        "mobile": "9876543215", "password": "Password123!", "confirmPassword": "Password123!"
    })
    res = client.post('/api/auth/login', json={
        "identifier": "LoginUser1@",
        "password": "Password123!"
    })
    assert res.status_code == 200
    assert res.get_json()["success"] is True

def test_5_invalid_password(client):
    client.post('/api/auth/register', json={
        "fullName": "Pass User", "username": "PassUser1@", "email": "pass@example.com",
        "mobile": "9876543216", "password": "Password123!", "confirmPassword": "Password123!"
    })
    res = client.post('/api/auth/login', json={
        "identifier": "PassUser1@",
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
        "fullName": "Logout User", "username": "LogoutUser1@", "email": "logout@example.com",
        "mobile": "9876543217", "password": "Password123!", "confirmPassword": "Password123!"
    })
    login_res = client.post('/api/auth/login', json={"identifier": "LogoutUser1@", "password": "Password123!"})
    csrf_token = login_res.get_json()["csrfToken"]
    res = client.post('/api/auth/logout', headers={"X-CSRF-Token": csrf_token})
    assert res.status_code == 200
    assert res.get_json()["success"] is True

def test_8_authenticated_endpoint(client):
    client.post('/api/auth/register', json={
        "fullName": "Me User", "username": "MeUser1@", "email": "me@example.com",
        "mobile": "9876543218", "password": "Password123!", "confirmPassword": "Password123!"
    })
    client.post('/api/auth/login', json={"identifier": "MeUser1@", "password": "Password123!"})
    res = client.get('/api/auth/me')
    assert res.status_code == 200
    assert res.get_json()["user"]["username"] == "MeUser1@"

def test_9_unauthenticated_endpoint_returns_401(client):
    res = client.get('/api/auth/me')
    assert res.status_code == 401
    assert "Authentication required" in res.get_json()["error"]

def test_10_wrong_role_returns_403(client):
    reg_res = client.post('/api/auth/register', json={
        "fullName": "Normal User", "username": "NormalUser1@", "email": "normal@example.com",
        "mobile": "9876543219", "password": "Password123!", "confirmPassword": "Password123!",
        "role": "user"
    })
    assert reg_res.status_code == 400
    assert "Allowed roles are 'operator' and 'admin'." in reg_res.get_json()["error"]

def test_11_admin_access_allowed(client):
    client.post('/api/auth/register', json={
        "fullName": "Admin User", "username": "AdminUser1@", "email": "admin@example.com",
        "mobile": "9876543220", "password": "Password123!", "confirmPassword": "Password123!",
        "role": "admin", "adminKey": Config.ADMIN_REGISTRATION_KEY
    })
    client.post('/api/auth/login', json={"identifier": "AdminUser1@", "password": "Password123!"})
    res = client.get('/api/admin/users')
    assert res.status_code == 200
    assert res.get_json()["success"] is True

def test_12_operator_access_denied_from_admin_endpoint(client):
    client.post('/api/auth/register', json={
        "fullName": "Operator User", "username": "OpUser1@", "email": "op@example.com",
        "mobile": "9876543221", "password": "Password123!", "confirmPassword": "Password123!",
        "role": "operator"
    })
    client.post('/api/auth/login', json={"identifier": "OpUser1@", "password": "Password123!"})
    res = client.get('/api/admin/users')
    assert res.status_code == 403
    assert "Access denied" in res.get_json()["error"]

def test_13_normal_user_access_denied_from_admin_endpoint(client):
    client.post('/api/auth/register', json={
        "fullName": "Basic User", "username": "BasicUser1@", "email": "basic@example.com",
        "mobile": "9876543222", "password": "Password123!", "confirmPassword": "Password123!"
    })
    client.post('/api/auth/login', json={"identifier": "BasicUser1@", "password": "Password123!"})
    res = client.get('/api/admin/users')
    assert res.status_code == 403
    assert "Access denied" in res.get_json()["error"]

# --- 14. Username and Password Complexity Tests ---
def test_14_username_and_password_complexity_validation(client):
    base_payload = {
        "fullName": "Test Complex",
        "username": "Abcd1234@",
        "email": "complex@example.com",
        "mobile": "9876543230",
        "password": "Abcd1234@",
        "confirmPassword": "Abcd1234@",
        "role": "operator"
    }

    # 1. Valid username & password succeeds
    res = client.post('/api/auth/register', json=base_payload)
    assert res.status_code == 201

    # 2. Invalid username: abc123 (too short, no upper, no spec)
    p = dict(base_payload, username="abc123", email="u1@example.com", mobile="9876543231")
    res = client.post('/api/auth/register', json=p)
    assert res.status_code == 400
    assert "Username must be" in res.get_json()["error"]

    # 3. Invalid username: Abcdefgh (no number, no spec)
    p = dict(base_payload, username="Abcdefgh", email="u2@example.com", mobile="9876543232")
    res = client.post('/api/auth/register', json=p)
    assert res.status_code == 400
    assert "Username must contain" in res.get_json()["error"]

    # 4. Invalid username: abcdefgh1 (no upper, no spec)
    p = dict(base_payload, username="abcdefgh1", email="u3@example.com", mobile="9876543233")
    res = client.post('/api/auth/register', json=p)
    assert res.status_code == 400

    # 5. Invalid username: ABCDEFGH1@ (no lower)
    p = dict(base_payload, username="ABCDEFGH1@", email="u4@example.com", mobile="9876543234")
    res = client.post('/api/auth/register', json=p)
    assert res.status_code == 400

    # 6. Invalid username: Abcdefgh@ (no number)
    p = dict(base_payload, username="Abcdefgh@", email="u5@example.com", mobile="9876543235")
    res = client.post('/api/auth/register', json=p)
    assert res.status_code == 400

    # 7. Invalid password: abc123
    p = dict(base_payload, username="ValidUser1@", password="abc123", confirmPassword="abc123", email="p1@example.com", mobile="9876543236")
    res = client.post('/api/auth/register', json=p)
    assert res.status_code == 400

    # 8. Invalid password: Abcdefgh (no number, no spec)
    p = dict(base_payload, username="ValidUser1@", password="Abcdefgh", confirmPassword="Abcdefgh", email="p2@example.com", mobile="9876543237")
    res = client.post('/api/auth/register', json=p)
    assert res.status_code == 400

    # 9. Invalid password: Abcd12345 (no spec)
    p = dict(base_payload, username="ValidUser1@", password="Abcd12345", confirmPassword="Abcd12345", email="p3@example.com", mobile="9876543238")
    res = client.post('/api/auth/register', json=p)
    assert res.status_code == 400

    # 10. Empty username / password rejected
    p = dict(base_payload, username="", email="empty@example.com", mobile="9876543239")
    res = client.post('/api/auth/register', json=p)
    assert res.status_code == 400
    assert "Missing required fields" in res.get_json()["error"]
