import logging
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logger():
    """Setup file logger for debugging with rotation"""
    # Get the directory where the executable/script is located
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        app_dir = Path(sys.executable).parent
    else:
        # Running as script
        app_dir = Path(__file__).parent
    
    log_file = app_dir / "dfg-funk-debug.log"
    
    # Create logger
    logger = logging.getLogger('DFG-Funk')
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Rotating File handler - max 5 MB per file, keep 3 backup files
    file_handler = RotatingFileHandler(
        log_file, 
        mode='a', 
        maxBytes=5*1024*1024,  # 5 MB
        backupCount=3,          # Keep 3 old files (total max ~20 MB)
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler - only if not frozen (for development)
    if not getattr(sys, 'frozen', False):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # Formatter for file
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Log startup
    logger.info("=" * 80)
    logger.info(f"DFG-Funk Client gestartet")
    logger.info(f"Log-Datei: {log_file}")
    logger.info(f"Python Version: {sys.version}")
    logger.info(f"Executable: {getattr(sys, 'frozen', False)}")
    logger.info("=" * 80)
    
    return logger


def log_exception(logger, exc_info=None):
    """Log an exception with full traceback"""
    if exc_info is None:
        exc_info = sys.exc_info()
    
    if exc_info and exc_info[0] is not None:
        logger.exception("Exception occurred:", exc_info=exc_info)
    else:
        logger.error("Exception occurred but no exception info available")
