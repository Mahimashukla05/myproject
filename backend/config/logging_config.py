import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(app=None):
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'app.log')
    
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s (%(lineno)d): %(message)s'
    )
    
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    logger = logging.getLogger("parcel_routing_app")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
    if app:
        app.logger.handlers = logger.handlers
        app.logger.setLevel(logger.level)
        
    logger.info("Application logging initialized successfully")
    return logger
