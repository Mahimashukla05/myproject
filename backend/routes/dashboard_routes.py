import logging
from flask import Blueprint, request, jsonify
from services.dashboard_service import DashboardService
from utils.auth_middleware import roles_required

logger = logging.getLogger("parcel_routing_app")
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/summary', methods=['GET'])
@dashboard_bp.route('/summary/', methods=['GET'])
@roles_required('admin', 'operator')
def get_dashboard_summary():
    period = request.args.get('period', 'all')
    res, status_code = DashboardService.get_summary(period)
    return jsonify(res), status_code
