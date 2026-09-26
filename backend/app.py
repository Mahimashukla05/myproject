from flask import Flask, jsonify
from flask_cors import CORS
from config.settings import Config
from config.logging_config import setup_logging
from config.db import Database
from routes.health_routes import health_bp
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.parcel_routes import parcel_bp
from routes.batch_routes import batch_bp
from routes.dashboard_routes import dashboard_bp
from routes.rule_routes import rule_bp
from routes.operator_routes import operator_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Enable CORS strictly for configured origins with credentials
    CORS(app, supports_credentials=True, origins=Config.ALLOWED_ORIGINS)

    # Setup Logging
    logger = setup_logging(app)
    logger.info("Initializing Flask application")

    # Connect to MongoDB
    Database.connect()

    # Register Blueprints
    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(operator_bp, url_prefix='/api/operator')
    app.register_blueprint(parcel_bp, url_prefix='/api/parcels')
    app.register_blueprint(batch_bp, url_prefix='/api/parcels')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(rule_bp, url_prefix='/api')

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Server error: {error}")
        return jsonify({"error": "Internal server error"}), 500

    return app

app = create_app()

if __name__ == '__main__':
    logger = setup_logging()
    logger.info(f"Starting server on port {Config.PORT}")
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)
