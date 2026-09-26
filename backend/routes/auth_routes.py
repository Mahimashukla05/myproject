from flask import Blueprint, request, jsonify, session, g
import logging
from services.auth_service import AuthService
from utils.auth_middleware import login_required, generate_csrf_token
from models.user_model import UserModel

logger = logging.getLogger("parcel_routing_app")
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    res, status_code = AuthService.register_user(data)
    return jsonify(res), status_code

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    identifier = data.get('identifier')
    password = data.get('password')
    client_ip = request.remote_addr or "unknown"

    res, status_code = AuthService.login_user(identifier, password, client_ip)
    if status_code == 200:
        session['user_id'] = res['user']['id']
        session.permanent = True
        csrf_token = generate_csrf_token()
        res['csrfToken'] = csrf_token
    return jsonify(res), status_code

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    user_id = session.get('user_id')
    if user_id:
        user = UserModel.find_by_id(user_id)
        if user:
            logger.info(f"User '{user.get('username')}' logged out")
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"}), 200

@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    csrf_token = generate_csrf_token()
    return jsonify({
        "success": True,
        "user": UserModel.to_dict(g.current_user),
        "csrfToken": csrf_token
    }), 200

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json() or {}
    identifier = data.get('identifier')
    res, status_code = AuthService.request_password_reset(identifier)
    return jsonify(res), status_code
