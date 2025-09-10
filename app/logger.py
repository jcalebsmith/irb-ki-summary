"""
Logging configuration for the IRB KI Summary application.
Provides consistent logging across all modules.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

# Import logging config
from config import LOGGING_CONFIG

def setup_logger(
    name: str = "irb_ki_summary",
    level: Optional[str] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with consistent formatting and handlers.
    
    Args:
        name: Logger name (typically module name)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Use config or provided level
    log_level = level or LOGGING_CONFIG["level"]
    logger.setLevel(getattr(logging, log_level))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(LOGGING_CONFIG["format"])
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    file_path = log_file or LOGGING_CONFIG.get("file")
    if file_path:
        try:
            # Ensure log directory exists
            log_path = Path(file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=LOGGING_CONFIG["max_bytes"],
                backupCount=LOGGING_CONFIG["backup_count"]
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not set up file logging: {e}")
    
    return logger

# Create default application logger
app_logger = setup_logger("irb_ki_summary")

# Convenience functions for module-specific loggers
def get_logger(module_name: str) -> logging.Logger:
    """Get a logger for a specific module."""
    return setup_logger(f"irb_ki_summary.{module_name}")

# Export commonly used log levels for convenience
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL