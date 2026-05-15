import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger():
    """
    Configures the root logger with a RotatingFileHandler and a StreamHandler.
    """
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    # Remove existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()

    # Rotating File Handler (max 5MB per file, keep 3 backups)
    log_file = os.path.join(os.path.dirname(__file__), 'portfolio_manager.log')
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# Call setup_logger on import so it's configured application-wide
setup_logger()
