import logging
from flask import Blueprint, request, jsonify, g
from services.batch_service import BatchService
from models.audit_model import AuditModel
from utils.auth_middleware import roles_required

logger = logging.getLogger("parcel_routing_app")
batch_bp = Blueprint('batch', __name__)

@batch_bp.route('/batch', methods=['POST'])
@batch_bp.route('/batch/', methods=['POST'])
@roles_required('admin', 'operator')
def upload_batch():
    def log_format_error():
        actor_id = str(g.current_user.get("_id") or g.current_user.get("id"))
        actor_username = g.current_user.get("username", "operator")
        actor_role = g.current_user.get("role", "operator")
        AuditModel.log_event(
            actor_id=actor_id,
            actor_username=actor_username,
            actor_role=actor_role,
            action="BATCH_UPLOAD",
            parcel_id=None,
            details={
                "fileType": "UNKNOWN",
                "total": 0,
                "successful": 0,
                "failed": 0,
                "outcome": "FORMAT_ERROR"
            }
        )

    if 'file' not in request.files:
        log_format_error()
        return jsonify({"success": False, "error": "No file parameter provided in request."}), 400

    file_item = request.files['file']
    if not file_item or file_item.filename == '':
        log_format_error()
        return jsonify({"success": False, "error": "No file selected for upload."}), 400

    user_id = str(g.current_user.get("_id") or g.current_user.get("id"))

    res, status_code = BatchService.process_batch(
        file_obj=file_item.stream,
        filename=file_item.filename,
        content_type=file_item.content_type,
        user_id=user_id,
        user_info=g.current_user
    )

    return jsonify(res), status_code
