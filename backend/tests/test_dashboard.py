import pytest
import sys
import os
from datetime import datetime, timezone, timedelta

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
                if isinstance(v, dict) and "$gte" in v:
                    if d.get(k, "") < v["$gte"]:
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
    app.config['SECRET_KEY'] = 'test-dashboard-secret'
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

# --- 1. Admin Can Access Dashboard ---
def test_admin_can_access_dashboard(client):
    csrf = helper_register_and_login(client, "admin_dash_user", role="admin")
    res = client.get('/api/dashboard/summary', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    assert res.get_json()["success"] is True

# --- 2. Operator Can Access Dashboard ---
def test_operator_can_access_dashboard(client):
    csrf = helper_register_and_login(client, "op_dash_user", role="operator")
    res = client.get('/api/dashboard/summary', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    assert res.get_json()["success"] is True

# --- 3. Normal User Registration Rejected ---
def test_normal_user_registration_rejected(client):
    res = client.post('/api/auth/register', json={
        "fullName": "Normal User", "username": "normal_dash_user", "email": "dash_user@example.com",
        "mobile": "9966554433", "password": "Password123!", "confirmPassword": "Password123!",
        "role": "user"
    })
    assert res.status_code == 400
    assert "Allowed roles are 'operator' and 'admin'." in res.get_json()["error"]

# --- 4. Unauthenticated Gets 401 ---
def test_unauthenticated_gets_401_on_dashboard(client):
    res = client.get('/api/dashboard/summary')
    assert res.status_code == 401

# --- 5. All-Time Metrics Correct ---
def test_all_time_metrics_correct(client):
    csrf = helper_register_and_login(client, "op_alltime", role="operator")
    
    # Create sample parcels
    p1 = ParcelModel.create_parcel({"parcelId": "P-DASH-1", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 0.5, "valueEur": 50, "submittedBy": "u1"})
    ParcelModel.update_parcel_routing("P-DASH-1", {"department": "MAIL", "insuranceRequired": False, "insuranceStatus": "NOT_REQUIRED", "status": "COMPLETED"})

    p2 = ParcelModel.create_parcel({"parcelId": "P-DASH-2", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 5.0, "valueEur": 1500, "submittedBy": "u1"})
    ParcelModel.update_parcel_routing("P-DASH-2", {"department": "REGULAR", "insuranceRequired": True, "insuranceStatus": "PENDING", "status": "AWAITING_INSURANCE"})

    res = client.get('/api/dashboard/summary?period=all', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    data = res.get_json()
    assert data["totalParcels"] == 2
    assert data["successfullyProcessed"] == 1
    assert data["insurancePending"] == 1
    assert data["departmentDistribution"]["mail"] == 1
    assert data["departmentDistribution"]["regular"] == 1

# --- 6. Today Filter Correct ---
def test_today_filter_correct(client):
    csrf = helper_register_and_login(client, "op_today", role="operator")
    
    # Today parcel
    ParcelModel.create_parcel({"parcelId": "P-TODAY-1", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10, "submittedBy": "u1"})

    # Yesterday parcel
    yesterday_iso = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    old_parcel = ParcelModel.create_parcel({"parcelId": "P-OLD-1", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10, "submittedBy": "u1"})
    ParcelModel.update_parcel_status("P-OLD-1", "RECEIVED", {"submittedAt": yesterday_iso})

    res = client.get('/api/dashboard/summary?period=today', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    data = res.get_json()
    assert data["period"] == "today"
    assert data["totalParcels"] == 1

# --- 7. Week Filter Correct ---
def test_week_filter_correct(client):
    csrf = helper_register_and_login(client, "op_week", role="operator")
    
    # Parcel submitted today (inside current calendar week)
    ParcelModel.create_parcel({"parcelId": "P-WEEK-NOW", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10, "submittedBy": "u1"})

    # Parcel submitted 10 days ago (outside current calendar week)
    old_week_iso = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    old_p = ParcelModel.create_parcel({"parcelId": "P-WEEK-OLD", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10, "submittedBy": "u1"})
    ParcelModel.update_parcel_status("P-WEEK-OLD", "RECEIVED", {"submittedAt": old_week_iso})

    res = client.get('/api/dashboard/summary?period=week', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    data = res.get_json()
    assert data["period"] == "week"
    assert data["totalParcels"] == 1

# --- 8. Department Distribution Correct ---
def test_department_distribution_correct(client):
    csrf = helper_register_and_login(client, "op_dept_dist", role="operator")
    
    p1 = ParcelModel.create_parcel({"parcelId": "P-M1", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 0.5, "valueEur": 50, "submittedBy": "u1"})
    ParcelModel.update_parcel_routing("P-M1", {"department": "MAIL", "insuranceRequired": False, "insuranceStatus": "NOT_REQUIRED", "status": "ROUTING_EVALUATED"})

    p2 = ParcelModel.create_parcel({"parcelId": "P-H1", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 15.0, "valueEur": 50, "submittedBy": "u1"})
    ParcelModel.update_parcel_routing("P-H1", {"department": "HEAVY", "insuranceRequired": False, "insuranceStatus": "NOT_REQUIRED", "status": "ROUTING_EVALUATED"})

    res = client.get('/api/dashboard/summary', headers={"X-CSRF-Token": csrf})
    data = res.get_json()["departmentDistribution"]
    assert data["mail"] == 1
    assert data["heavy"] == 1
    assert data["regular"] == 0

# --- 9. Insurance Pending Count Correct ---
def test_insurance_pending_count_correct(client):
    csrf = helper_register_and_login(client, "op_inspending", role="operator")
    
    p = ParcelModel.create_parcel({"parcelId": "P-INSP", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 2.0, "valueEur": 2000, "submittedBy": "u1"})
    ParcelModel.update_parcel_routing("P-INSP", {"department": "REGULAR", "insuranceRequired": True, "insuranceStatus": "PENDING", "status": "AWAITING_INSURANCE"})

    res = client.get('/api/dashboard/summary', headers={"X-CSRF-Token": csrf})
    assert res.get_json()["insurancePending"] == 1

# --- 10. Insurance Rejected Count Correct ---
def test_insurance_rejected_count_correct(client):
    csrf = helper_register_and_login(client, "op_insrej", role="operator")
    
    p = ParcelModel.create_parcel({"parcelId": "P-INSREJ", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 2.0, "valueEur": 2000, "submittedBy": "u1"})
    ParcelModel.update_parcel_status("P-INSREJ", "INSURANCE_REJECTED", {"insuranceStatus": "REJECTED", "failureReason": "High risk"})

    res = client.get('/api/dashboard/summary', headers={"X-CSRF-Token": csrf})
    assert res.get_json()["insuranceRejected"] == 1

# --- 11. Completed Count Correct ---
def test_completed_count_correct(client):
    csrf = helper_register_and_login(client, "op_comp", role="operator")
    
    p = ParcelModel.create_parcel({"parcelId": "P-COMP", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 50, "submittedBy": "u1"})
    ParcelModel.update_parcel_status("P-COMP", "COMPLETED")

    res = client.get('/api/dashboard/summary', headers={"X-CSRF-Token": csrf})
    assert res.get_json()["successfullyProcessed"] == 1

# --- 12. Failed Count Correct ---
def test_failed_count_correct(client):
    csrf = helper_register_and_login(client, "op_fail", role="operator")
    
    p = ParcelModel.create_parcel({"parcelId": "P-FAIL", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 50, "submittedBy": "u1"})
    ParcelModel.update_parcel_status("P-FAIL", "FAILED", {"failureReason": "Damaged"})

    res = client.get('/api/dashboard/summary', headers={"X-CSRF-Token": csrf})
    assert res.get_json()["failed"] == 1

# --- 13. Empty Database Returns Genuine Zero/Empty Values ---
def test_empty_database_returns_genuine_zero_values(client):
    csrf = helper_register_and_login(client, "op_empty_db", role="operator")
    res = client.get('/api/dashboard/summary', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    data = res.get_json()
    assert data["totalParcels"] == 0
    assert data["successfullyProcessed"] == 0
    assert data["failed"] == 0
    assert data["insurancePending"] == 0
    assert data["insuranceRejected"] == 0
    assert data["departmentDistribution"] == {"mail": 0, "regular": 0, "heavy": 0}

# --- 14. Database Failure Returns Explicit Error ---
def test_database_failure_returns_explicit_error(client, monkeypatch):
    csrf = helper_register_and_login(client, "op_db_offline", role="operator")
    monkeypatch.setattr("models.parcel_model.ParcelModel.get_dashboard_summary", staticmethod(lambda period="all": None))
    res = client.get('/api/dashboard/summary', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 503
    assert res.get_json()["errorType"] == "TECHNICAL"

# --- 15. Admin Can See All Parcels ---
def test_admin_can_see_all_parcels(client):
    admin_csrf = helper_register_and_login(client, "admin_list", role="admin")
    ParcelModel.create_parcel({"parcelId": "P-ALL-1", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10, "submittedBy": "other_user"})
    
    res = client.get('/api/parcels', headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 200
    assert res.get_json()["total"] >= 1

# --- 16. Operator Can See All Parcels ---
def test_operator_can_see_all_parcels(client):
    op_csrf = helper_register_and_login(client, "op_list", role="operator")
    ParcelModel.create_parcel({"parcelId": "P-ALL-2", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10, "submittedBy": "other_user"})
    
    res = client.get('/api/parcels', headers={"X-CSRF-Token": op_csrf})
    assert res.status_code == 200
    assert res.get_json()["total"] >= 1

# --- 17 & 18. Normal User Role Registration Rejected ---
def test_normal_user_role_registration_rejected(client):
    res1 = client.post('/api/auth/register', json={
        "fullName": "User Scoped", "username": "user_scoped", "email": "scoped@example.com",
        "mobile": "9966554422", "password": "Password123!", "confirmPassword": "Password123!",
        "role": "user"
    })
    assert res1.status_code == 400
    assert "Allowed roles are 'operator' and 'admin'." in res1.get_json()["error"]

# --- 19. Status Filter Works ---
def test_status_filter_works(client):
    csrf = helper_register_and_login(client, "op_stat_filt", role="operator")
    p1 = ParcelModel.create_parcel({"parcelId": "P-REC", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10, "submittedBy": "u1"})
    p2 = ParcelModel.create_parcel({"parcelId": "P-CMP", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10, "submittedBy": "u1"})
    ParcelModel.update_parcel_status("P-CMP", "COMPLETED")

    res = client.get('/api/parcels?status=COMPLETED', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    items = res.get_json()["items"]
    assert len(items) == 1
    assert items[0]["parcelId"] == "P-CMP"

# --- 20. Department Filter Works ---
def test_department_filter_works(client):
    csrf = helper_register_and_login(client, "op_dept_filt", role="operator")
    p1 = ParcelModel.create_parcel({"parcelId": "P-D-MAIL", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 0.5, "valueEur": 10, "submittedBy": "u1"})
    ParcelModel.update_parcel_routing("P-D-MAIL", {"department": "MAIL", "insuranceRequired": False, "insuranceStatus": "NOT_REQUIRED", "status": "ROUTING_EVALUATED"})

    res = client.get('/api/parcels?department=MAIL', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    items = res.get_json()["items"]
    assert len(items) == 1
    assert items[0]["parcelId"] == "P-D-MAIL"

# --- 21. Insurance Status Filter Works ---
def test_insurance_status_filter_works(client):
    csrf = helper_register_and_login(client, "op_ins_stat_filt", role="operator")
    p1 = ParcelModel.create_parcel({"parcelId": "P-D-PEND", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 2.0, "valueEur": 2000, "submittedBy": "u1"})
    ParcelModel.update_parcel_routing("P-D-PEND", {"department": "REGULAR", "insuranceRequired": True, "insuranceStatus": "PENDING", "status": "AWAITING_INSURANCE"})

    res = client.get('/api/parcels?insuranceStatus=PENDING', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    items = res.get_json()["items"]
    assert len(items) == 1
    assert items[0]["parcelId"] == "P-D-PEND"

# --- 22. Parcel ID Filter Works ---
def test_parcel_id_filter_works(client):
    csrf = helper_register_and_login(client, "op_pid_filt", role="operator")
    ParcelModel.create_parcel({"parcelId": "PCL-SEARCH-99", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10, "submittedBy": "u1"})

    res = client.get('/api/parcels?parcelId=PCL-SEARCH-99', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    items = res.get_json()["items"]
    assert len(items) == 1
    assert items[0]["parcelId"] == "PCL-SEARCH-99"

# --- 23. Pagination Works ---
def test_pagination_works(client):
    csrf = helper_register_and_login(client, "op_page_test", role="operator")
    for i in range(5):
        ParcelModel.create_parcel({"parcelId": f"P-PAG-{i}", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10, "submittedBy": "u1"})

    res1 = client.get('/api/parcels?page=1&limit=2', headers={"X-CSRF-Token": csrf})
    assert res1.status_code == 200
    body1 = res1.get_json()
    assert body1["page"] == 1
    assert body1["limit"] == 2
    assert len(body1["items"]) == 2
    assert body1["total"] == 5
    assert body1["totalPages"] == 3

# --- 24. Newest-First Ordering Works ---
def test_newest_first_ordering_works(client):
    csrf = helper_register_and_login(client, "op_order_test", role="operator")
    p1 = ParcelModel.create_parcel({"parcelId": "P-FIRST", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10, "submittedBy": "u1"})
    ParcelModel.update_parcel_status("P-FIRST", "RECEIVED", {"submittedAt": "2026-01-01T00:00:00Z"})

    p2 = ParcelModel.create_parcel({"parcelId": "P-SECOND", "senderName": "A", "senderContact": "1", "receiverName": "B", "receiverContact": "2", "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10, "submittedBy": "u1"})
    ParcelModel.update_parcel_status("P-SECOND", "RECEIVED", {"submittedAt": "2026-06-01T00:00:00Z"})

    res = client.get('/api/parcels?sort=-submittedAt', headers={"X-CSRF-Token": csrf})
    items = res.get_json()["items"]
    assert items[0]["parcelId"] == "P-SECOND"
    assert items[1]["parcelId"] == "P-FIRST"

# --- 25. Invalid Pagination/Sort Input Is Safely Handled ---
def test_invalid_pagination_sort_input_safely_handled(client):
    csrf = helper_register_and_login(client, "op_invalid_input", role="operator")
    res = client.get('/api/parcels?page=-5&limit=abc&sort={$gt:""}', headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    body = res.get_json()
    assert body["page"] == 1
    assert body["limit"] == 20

# --- 26. Authorized Roles Can View Parcel Details ---
def test_authorized_roles_can_view_parcel_details(client):
    op_csrf = helper_register_and_login(client, "op_det", role="operator")
    create_res = client.post('/api/parcels', json={
        "senderName": "A", "senderContact": "123", "receiverName": "B", "receiverContact": "456",
        "origin": "X", "destination": "Y", "weightKg": 1.0, "valueEur": 10
    }, headers={"X-CSRF-Token": op_csrf})
    parcel_id = create_res.get_json()["parcel"]["parcelId"]

    admin_csrf = helper_register_and_login(client, "admin_det", role="admin")
    res = client.get(f'/api/parcels/{parcel_id}', headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 200
    assert res.get_json()["parcel"]["parcelId"] == parcel_id

# --- 27 & 28. Normal User Registration Rejected ---
def test_normal_user_details_registration_rejected(client):
    res = client.post('/api/auth/register', json={
        "fullName": "User Details", "username": "user_own_det", "email": "details@example.com",
        "mobile": "9966554411", "password": "Password123!", "confirmPassword": "Password123!",
        "role": "user"
    })
    assert res.status_code == 400
    assert "Allowed roles are 'operator' and 'admin'." in res.get_json()["error"]

# --- 29. Nonexistent Parcel Returns 404 ---
def test_nonexistent_parcel_returns_404(client):
    admin_csrf = helper_register_and_login(client, "admin_404", role="admin")
    res = client.get('/api/parcels/PCL-NOEXIST999', headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 404
