import re
import time
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from models.user_model import UserModel
from config.settings import Config

logger = logging.getLogger("parcel_routing_app")

# In-memory store for rate-limiting failed login attempts: {key: [timestamp1, timestamp2]}
_failed_login_attempts = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 15 * 60  # 15 minutes

def _is_rate_limited(key):
    now = time.time()
    attempts = _failed_login_attempts.get(key, [])
    # Filter attempts within window
    valid_attempts = [t for t in attempts if now - t < LOCKOUT_DURATION_SECONDS]
    _failed_login_attempts[key] = valid_attempts
    return len(valid_attempts) >= MAX_FAILED_ATTEMPTS

def _record_failed_attempt(key):
    now = time.time()
    attempts = _failed_login_attempts.get(key, [])
    attempts.append(now)
    _failed_login_attempts[key] = attempts

def _clear_failed_attempts(key):
    _failed_login_attempts.pop(key, None)

class AuthService:
    VALID_ROLES = ["admin", "operator", "user"]

    @classmethod
    def register_user(cls, data):
        if not isinstance(data, dict):
            return {"success": False, "error": "Invalid request payload format."}, 400

        fullName = str(data.get("fullName", "") or "").strip()
        username = str(data.get("username", "") or "").strip()
        email = str(data.get("email", "") or "").strip()
        mobile = str(data.get("mobile", "") or "").strip()
        password = str(data.get("password", "") or "")
        confirmPassword = str(data.get("confirmPassword", "") or "")
        requested_role = str(data.get("role", "user") or "user").lower().strip()
        adminKey = str(data.get("adminKey", "") or "").strip()

        # 1. Required fields check
        missing = []
        if not fullName: missing.append("Full Name")
        if not username: missing.append("Username")
        if not email: missing.append("Email")
        if not mobile: missing.append("Mobile Number")
        if not password: missing.append("Password")
        if not confirmPassword: missing.append("Confirm Password")
        if missing:
            return {"success": False, "error": f"Missing required fields: {', '.join(missing)}"}, 400

        # 2. Confirm password match
        if password != confirmPassword:
            return {"success": False, "error": "Password and Confirm Password do not match."}, 400

        # 3. 10-digit Indian Mobile validation (Requirement 11)
        clean_mobile = re.sub(r'[\s\-+]', '', mobile)
        if not re.match(r'^[6-9]\d{9}$', clean_mobile):
            return {"success": False, "error": "Invalid mobile number. Must be a valid 10-digit Indian mobile number (e.g. 9876543210)."}, 400

        # 4. Email format check
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return {"success": False, "error": "Invalid email address format."}, 400

        # 5. Password strength check (min 8 chars)
        if len(password) < 8:
            return {"success": False, "error": "Password must be at least 8 characters long."}, 400

        # 6. Role validation & Server-Side Admin Security Check (Requirement 10)
        if requested_role not in cls.VALID_ROLES:
            return {"success": False, "error": "Invalid user role specified."}, 400

        if requested_role == "admin":
            if not adminKey or adminKey != Config.ADMIN_REGISTRATION_KEY:
                logger.warning(f"Unauthorized Admin registration attempt for username '{username}'")
                return {"success": False, "error": "Invalid Admin registration key. Admin creation is restricted."}, 403

        # 7. Uniqueness checks
        if UserModel.find_by_username(username):
            return {"success": False, "error": "Username is already taken."}, 400
        if UserModel.find_by_email(email):
            return {"success": False, "error": "Email address is already registered."}, 400
        if UserModel.find_by_mobile(clean_mobile):
            return {"success": False, "error": "Mobile number is already registered."}, 400

        # 8. Create User with hashed password
        password_hash = generate_password_hash(password)
        user_doc = UserModel.create_user({
            "fullName": fullName,
            "username": username,
            "email": email,
            "mobile": clean_mobile,
            "passwordHash": password_hash,
            "role": requested_role
        })

        logger.info(f"Account created successfully for user '{username}' with role '{requested_role}'")
        return {"success": True, "user": UserModel.to_dict(user_doc)}, 201

    @classmethod
    def login_user(cls, identifier, password, client_ip=""):
        if not isinstance(identifier, str) or not isinstance(password, str):
            return {"success": False, "error": "Invalid username, email, mobile number or password."}, 401

        clean_id = identifier.strip().lower()
        if not clean_id or not password:
            return {"success": False, "error": "Invalid username, email, mobile number or password."}, 401

        rate_key = f"{client_ip}:{clean_id}"
        if _is_rate_limited(rate_key):
            logger.warning(f"Rate limited login attempt for identifier '{clean_id}' from IP {client_ip}")
            return {"success": False, "error": "Too many failed login attempts. Please try again after 15 minutes."}, 429

        user = UserModel.find_by_identifier(clean_id)
        if not user or not check_password_hash(user.get("passwordHash", ""), password):
            _record_failed_attempt(rate_key)
            logger.warning(f"Failed login attempt for identifier '{clean_id}' from IP {client_ip}")
            return {"success": False, "error": "Invalid username, email, mobile number or password."}, 401

        if not user.get("isActive", True):
            logger.warning(f"Login attempt for inactive account '{user.get('username')}'")
            return {"success": False, "error": "Account is deactivated."}, 403

        _clear_failed_attempts(rate_key)
        logger.info(f"Successful login for user '{user.get('username')}' (role: {user.get('role')})")
        return {"success": True, "user": UserModel.to_dict(user)}, 200

    @classmethod
    def request_password_reset(cls, identifier):
        """Generic password reset response preventing user enumeration."""
        if not isinstance(identifier, str) or not identifier.strip():
            return {"success": True, "message": "If an account matches that identifier, password reset instructions have been recorded."}, 200

        user = UserModel.find_by_identifier(identifier.strip())
        if user:
            logger.info(f"Password reset requested for user '{user.get('username')}'")

        return {"success": True, "message": "If an account matches that identifier, password reset instructions have been recorded."}, 200
