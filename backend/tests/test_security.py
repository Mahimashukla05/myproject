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
    # Reset rate-limiting state
    from services.auth_service import _failed_login_attempts
    _failed_login_attempts.clear()

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-security-secret'
    with app.test_client() as client:
        yield client

def test_security_1_csrf_rejection_and_acceptance(client):
    # Register user
    client.post('/api/auth/register', json={
        "fullName": "CSRF User", "username": "csrfuser", "email": "csrf@example.com",
        "mobile": "9876543210", "password": "Password123!", "confirmPassword": "Password123!"
    })
    # Login & get session + CSRF token
    login_res = client.post('/api/auth/login', json={"identifier": "csrfuser", "password": "Password123!"})
    csrf_token = login_res.get_json()["csrfToken"]

    # State-changing request WITHOUT CSRF header -> 403 Forbidden
    bad_logout = client.post('/api/auth/logout')
    assert bad_logout.status_code == 403
    assert "CSRF token missing or invalid" in bad_logout.get_json()["error"]

    # State-changing request WITH valid CSRF header -> 200 OK
    good_logout = client.post('/api/auth/logout', headers={"X-CSRF-Token": csrf_token})
    assert good_logout.status_code == 200

def test_security_2_rate_limiting_brute_force(client):
    client.post('/api/auth/register', json={
        "fullName": "Brute User", "username": "bruteuser", "email": "brute@example.com",
        "mobile": "9876543211", "password": "Password123!", "confirmPassword": "Password123!"
    })

    # Fail 5 times
    for _ in range(5):
        res = client.post('/api/auth/login', json={"identifier": "bruteuser", "password": "WrongPassword!"})
        assert res.status_code == 401

    # 6th attempt should be rate-limited with 429 Too Many Requests
    blocked_res = client.post('/api/auth/login', json={"identifier": "bruteuser", "password": "Password123!"})
    assert blocked_res.status_code == 429
    assert "Too many failed login attempts" in blocked_res.get_json()["error"]

def test_security_3_cookie_security_flags(client):
    client.post('/api/auth/register', json={
        "fullName": "Cookie User", "username": "cookieuser", "email": "cookie@example.com",
        "mobile": "9876543212", "password": "Password123!", "confirmPassword": "Password123!"
    })
    res = client.post('/api/auth/login', json={"identifier": "cookieuser", "password": "Password123!"})
    
    # Check set-cookie header contains HttpOnly and SameSite=Lax
    cookies = res.headers.getlist('Set-Cookie')
    assert len(cookies) > 0
    session_cookie = cookies[0]
    assert "HttpOnly" in session_cookie
    assert "SameSite=Lax" in session_cookie

def test_security_4_generic_login_errors_prevent_user_enumeration(client):
    client.post('/api/auth/register', json={
        "fullName": "Enum User", "username": "enumuser", "email": "enum@example.com",
        "mobile": "9876543213", "password": "Password123!", "confirmPassword": "Password123!"
    })

    # Wrong password for existing user
    res1 = client.post('/api/auth/login', json={"identifier": "enumuser", "password": "WrongPassword!"})
    # Nonexistent user
    res2 = client.post('/api/auth/login', json={"identifier": "nonexistentuser", "password": "Password123!"})

    # Both must return identical 401 error message
    assert res1.status_code == 401
    assert res2.status_code == 401
    assert res1.get_json()["error"] == res2.get_json()["error"]
    assert res1.get_json()["error"] == "Invalid username, email, mobile number or password."

def test_security_5_admin_registration_protection(client):
    # Attempt Admin registration WITHOUT admin key -> 403 Forbidden
    res_bad = client.post('/api/auth/register', json={
        "fullName": "Fake Admin", "username": "fakeadmin", "email": "fakeadmin@example.com",
        "mobile": "9876543214", "password": "Password123!", "confirmPassword": "Password123!",
        "role": "admin", "adminKey": "wrong-secret-key"
    })
    assert res_bad.status_code == 403
    assert "Invalid Admin registration key" in res_bad.get_json()["error"]

    # Attempt Admin registration WITH valid admin key -> 201 Created
    res_good = client.post('/api/auth/register', json={
        "fullName": "Real Admin", "username": "realadmin", "email": "realadmin@example.com",
        "mobile": "9876543215", "password": "Password123!", "confirmPassword": "Password123!",
        "role": "admin", "adminKey": Config.ADMIN_REGISTRATION_KEY
    })
    assert res_good.status_code == 201
    assert res_good.get_json()["user"]["role"] == "admin"

def test_security_6_indian_mobile_number_validation(client):
    # Invalid mobile (not 10 digits or invalid prefix)
    res_bad = client.post('/api/auth/register', json={
        "fullName": "Bad Mobile", "username": "badmobile", "email": "mobile@example.com",
        "mobile": "12345", "password": "Password123!", "confirmPassword": "Password123!"
    })
    assert res_bad.status_code == 400
    assert "10-digit Indian mobile number" in res_bad.get_json()["error"]

    # Valid 10-digit Indian mobile (starts with 9)
    res_good = client.post('/api/auth/register', json={
        "fullName": "Good Mobile", "username": "goodmobile", "email": "goodmobile@example.com",
        "mobile": "9876543216", "password": "Password123!", "confirmPassword": "Password123!"
    })
    assert res_good.status_code == 201

def test_security_7_nosql_injection_prevention(client):
    # Send dict objects in JSON payload instead of strings
    res = client.post('/api/auth/login', json={
        "identifier": {"$ne": None},
        "password": {"$ne": None}
    })
    assert res.status_code == 401
    assert "Invalid username" in res.get_json()["error"]
