from flask import Blueprint, jsonify, request
from utils.auth_middleware import roles_required
from models.user_model import UserModel
from models.audit_model import AuditModel
from services.alert_service import AlertService

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/users', methods=['GET'])
@roles_required('admin')
def get_all_users():
    users = UserModel.get_all_users()
    return jsonify({"success": True, "users": users}), 200

@admin_bp.route('/test', methods=['GET'])
@roles_required('admin')
def admin_test():
    return jsonify({"success": True, "message": "Admin authorization check passed."}), 200

@admin_bp.route('/audit-logs', methods=['GET'])
@roles_required('admin')
def get_audit_logs():
    page = request.args.get('page', 1)
    limit = request.args.get('limit', 20)
    query_filters = {
        "action": request.args.get('action'),
        "actorUsername": request.args.get('actorUsername'),
        "actorRole": request.args.get('actorRole'),
        "parcelId": request.args.get('parcelId')
    }
    result = AuditModel.get_paginated_logs(page=page, limit=limit, query_filters=query_filters)
    return jsonify({
        "success": True,
        "logs": result["logs"],
        "page": result["page"],
        "limit": result["limit"],
        "total": result["total"],
        "totalPages": result["totalPages"]
    }), 200

@admin_bp.route('/alerts', methods=['GET'])
@roles_required('admin')
def get_admin_alerts():
    result = AlertService.get_admin_system_alerts()
    return jsonify(result), 200
