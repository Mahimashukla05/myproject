import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    PORT = int(os.getenv("PORT", 5000))
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/parcel_routing_db")
    ADMIN_REGISTRATION_KEY = os.getenv("ADMIN_REGISTRATION_KEY", "admin-secret-key-123")
    ALLOWED_ORIGINS = [
        origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()
    ]
    DEBUG = FLASK_ENV == "development"

    # Session & Security Cookie Settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true" or (os.getenv("FLASK_ENV", "development") == "production")
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # Batch Upload Settings
    MAX_BATCH_FILE_SIZE_BYTES = int(os.getenv("MAX_BATCH_FILE_SIZE_BYTES", 2 * 1024 * 1024))  # 2 MB default limit

