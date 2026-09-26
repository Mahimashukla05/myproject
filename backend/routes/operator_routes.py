from flask import Blueprint, jsonify, g
from utils.auth_middleware import roles_required
from services.alert_service import AlertService

operator_bp = Blueprint('operator', __name__)

@operator_bp.route('/alerts', methods=['GET'])
@roles_required('operator')
def get_operator_alerts():
    operator_id = str(g.current_user.get("_id") or g.current_user.get("id"))
    result = AlertService.get_operator_alerts(operator_id)
    return jsonify(result), 200
