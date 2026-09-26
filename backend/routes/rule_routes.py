import logging
from flask import Blueprint, request, jsonify, g
from services.rule_service import RuleService
from utils.auth_middleware import login_required, roles_required

logger = logging.getLogger("parcel_routing_app")
rule_bp = Blueprint('rules', __name__)

@rule_bp.route('/routing-rules/active', methods=['GET'])
@roles_required('admin', 'operator')
def get_active_rules():
    active_rules = RuleService.get_active_rule_set()
    return jsonify({"success": True, "activeRules": active_rules}), 200

@rule_bp.route('/routing-rules/history', methods=['GET'])
@roles_required('admin')
def get_rule_history():
    history = RuleService.get_rule_history()
    return jsonify({"success": True, "history": history}), 200

@rule_bp.route('/rule-change-requests', methods=['POST'])
@rule_bp.route('/rule-change-requests/', methods=['POST'])
@roles_required('operator')
def create_change_request():
    data = request.get_json() or {}
    res, status_code = RuleService.create_change_request(data, g.current_user)
    return jsonify(res), status_code

@rule_bp.route('/rule-change-requests', methods=['GET'])
@rule_bp.route('/rule-change-requests/', methods=['GET'])
@roles_required('admin', 'operator')
def get_change_requests():
    filters = {}
    status = request.args.get('status')
    if status:
        filters['status'] = status
    res, status_code = RuleService.get_change_requests(filters, g.current_user)
    return jsonify(res), status_code

@rule_bp.route('/rule-change-requests/<request_id>', methods=['GET'])
@roles_required('admin', 'operator')
def get_change_request(request_id):
    res, status_code = RuleService.get_change_request_by_id(request_id, g.current_user)
    return jsonify(res), status_code

@rule_bp.route('/rule-change-requests/<request_id>/approve', methods=['POST'])
@roles_required('admin')
def approve_change_request(request_id):
    data = request.get_json() or {}
    confirmation = data.get('confirmation') if 'confirmation' in data else data.get('confirm')
    res, status_code = RuleService.approve_change_request(request_id, g.current_user, confirmation=confirmation)
    return jsonify(res), status_code

@rule_bp.route('/rule-change-requests/<request_id>/reject', methods=['POST'])
@roles_required('admin')
def reject_change_request(request_id):
    data = request.get_json() or {}
    reason = data.get('reason', '')
    res, status_code = RuleService.reject_change_request(request_id, reason, g.current_user)
    return jsonify(res), status_code

@rule_bp.route('/rule-change-requests/<request_id>/withdraw', methods=['POST'])
@roles_required('operator')
def withdraw_change_request(request_id):
    res, status_code = RuleService.withdraw_change_request(request_id, g.current_user)
    return jsonify(res), status_code
