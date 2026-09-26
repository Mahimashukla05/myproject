from flask import Blueprint, jsonify
from config.db import Database

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    is_db_up = Database.is_connected()
    db_status = "connected" if is_db_up else "unavailable"
    return jsonify({
        "status": "healthy" if is_db_up else "degraded",
        "service": "Parcel Routing System API",
        "database": db_status
    }), 200
