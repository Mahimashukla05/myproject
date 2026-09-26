from flask import Blueprint, request, jsonify, g
import logging
from services.parcel_service import ParcelService
from services.routing_service import RoutingService
from services.lifecycle_service import LifecycleService
from models.parcel_model import ParcelModel
from utils.auth_middleware import login_required, roles_required

logger = logging.getLogger("parcel_routing_app")
parcel_bp = Blueprint('parcels', __name__)

@parcel_bp.route('', methods=['GET'])
@parcel_bp.route('/', methods=['GET'])
@login_required
def get_parcels():
    filters = {}
    insurance_status = request.args.get('insuranceStatus')
    status = request.args.get('status')
    department = request.args.get('department')
    parcel_id = request.args.get('parcelId')

    if insurance_status:
        filters['insuranceStatus'] = insurance_status
    if status:
        filters['status'] = status
    if department:
        filters['department'] = department
    if parcel_id:
        filters['parcelId'] = parcel_id

    page = request.args.get('page', 1)
    limit = request.args.get('limit', 20)
    sort = request.args.get('sort', '-submittedAt')

    user_id = str(g.current_user.get("_id") or g.current_user.get("id"))
    role = g.current_user.get("role", "user")

    res, status_code = ParcelService.get_paginated_parcels(
        query_filters=filters,
        user_id=user_id,
        role=role,
        page=page,
        limit=limit,
        sort_field=sort
    )
    return jsonify(res), status_code

@parcel_bp.route('', methods=['POST'])
@parcel_bp.route('/', methods=['POST'])
@roles_required('admin', 'operator')
def create_parcel():
    data = request.get_json() or {}
    user_id = str(g.current_user.get("_id") or g.current_user.get("id"))
    
    res, status_code = ParcelService.create_parcel(data, user_id)
    return jsonify(res), status_code

@parcel_bp.route('/<parcel_id>', methods=['GET'])
@login_required
def get_parcel(parcel_id):
    res, status_code = ParcelService.get_parcel(parcel_id, current_user=g.current_user)
    return jsonify(res), status_code

@parcel_bp.route('/<parcel_id>/route', methods=['POST'])
@roles_required('admin', 'operator')
def route_parcel(parcel_id):
    res, status_code = RoutingService.route_parcel(parcel_id)
    return jsonify(res), status_code

@parcel_bp.route('/<parcel_id>/insurance/approve', methods=['POST'])
@roles_required('admin')
def approve_insurance(parcel_id):
    res, status_code = LifecycleService.approve_insurance(parcel_id, g.current_user)
    return jsonify(res), status_code

@parcel_bp.route('/<parcel_id>/insurance/reject', methods=['POST'])
@roles_required('admin')
def reject_insurance(parcel_id):
    data = request.get_json() or {}
    reason = data.get("reason", "")
    res, status_code = LifecycleService.reject_insurance(parcel_id, reason, g.current_user)
    return jsonify(res), status_code

@parcel_bp.route('/<parcel_id>/assign', methods=['POST'])
@roles_required('admin', 'operator')
def assign_parcel(parcel_id):
    res, status_code = LifecycleService.transition_parcel(parcel_id, "ASSIGNED", "Parcel Assigned", g.current_user)
    return jsonify(res), status_code

@parcel_bp.route('/<parcel_id>/start-processing', methods=['POST'])
@roles_required('admin', 'operator')
def start_processing_parcel(parcel_id):
    res, status_code = LifecycleService.transition_parcel(parcel_id, "IN_PROCESSING", "Parcel Processing Started", g.current_user)
    return jsonify(res), status_code

@parcel_bp.route('/<parcel_id>/complete', methods=['POST'])
@roles_required('admin', 'operator')
def complete_parcel(parcel_id):
    res, status_code = LifecycleService.transition_parcel(parcel_id, "COMPLETED", "Parcel Completed", g.current_user)
    return jsonify(res), status_code
