import secrets
from functools import wraps
from flask import session, jsonify, g, request
import logging
from models.user_model import UserModel

logger = logging.getLogger("parcel_routing_app")

def generate_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]

def verify_csrf_token():
    """Verify CSRF token for cookie-authenticated state-changing requests."""
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        # Skip CSRF check for initial unauthenticated login and register calls
        if request.endpoint in ["auth.login", "auth.register"]:
            return None
        
        # If user is authenticated via cookie session, enforce CSRF header check
        if session.get("user_id"):
            token_header = request.headers.get("X-CSRF-Token")
            session_token = session.get("csrf_token")
            if not session_token or not token_header or not secrets.compare_digest(token_header, session_token):
                logger.warning(
                    f"CSRF validation failed for user_id '{session.get('user_id')}' "
                    f"on {request.path} from IP {request.remote_addr}"
                )
                return jsonify({"error": "CSRF token missing or invalid"}), 403
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        csrf_err = verify_csrf_token()
        if csrf_err:
            return csrf_err

        user_id = session.get("user_id")
        if not user_id:
            logger.warning(f"Unauthorized access attempt to {request.path} from IP {request.remote_addr}")
            return jsonify({"error": "Authentication required"}), 401
        
        user = UserModel.find_by_id(user_id)
        if not user or not user.get("isActive", True):
            session.clear()
            logger.warning(f"Invalid or inactive session for user_id {user_id}")
            return jsonify({"error": "Session invalid or expired"}), 401
        
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            csrf_err = verify_csrf_token()
            if csrf_err:
                return csrf_err

            user_id = session.get("user_id")
            if not user_id:
                logger.warning(f"Unauthorized access attempt to {request.path} from IP {request.remote_addr}")
                return jsonify({"error": "Authentication required"}), 401

            user = UserModel.find_by_id(user_id)
            if not user or not user.get("isActive", True):
                session.clear()
                return jsonify({"error": "Session invalid or expired"}), 401

            g.current_user = user
            user_role = user.get("role", "user")

            allowed_list = [r.lower() for r in allowed_roles]
            if user_role.lower() not in allowed_list:
                logger.warning(
                    f"Forbidden access attempt to {request.path} by user '{user.get('username')}' "
                    f"with role '{user_role}'. Required roles: {allowed_list}"
                )
                return jsonify({"error": "Access denied. Insufficient permissions."}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator
