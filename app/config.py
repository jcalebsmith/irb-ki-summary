"""
Centralized Configuration Management
All application settings in one place with environment variable support
"""
import os
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).parent.parent
APP_DIR = BASE_DIR / "app"
TEST_DATA_DIR = BASE_DIR / "test_data"

# Load environment variables
env_path = APP_DIR / '.env'
load_dotenv(env_path, override=True)

# Azure OpenAI configuration
AZURE_OPENAI_CONFIG = {
    "api_key": os.getenv("OPENAI_API_KEY"),
    "endpoint": os.getenv("OPENAI_API_BASE"),
    "api_version": os.getenv("API_VERSION", "2024-10-21"),
    "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_LLM", "gpt-4o"),
    "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.0")),
    "default_headers": {
        "OpenAI-Organization": os.getenv("ORGANIZATION", "231173"),
        "Shortcode": os.getenv("ORGANIZATION", "231173")
    },
}

# Text processing limits
TEXT_PROCESSING = {
    "max_tokens": 12000,
    "chunk_size": 2000,
    "max_words": {
        "short": 30,
        "medium": 50,
        "long": 100,
        "extra_long": 200
    }
}

# Validation configuration
VALIDATION_CONFIG = {
    "cv_target": 15.0,  # Coefficient of variation target < 15%
    "prohibited_phrases": [
        "[INSERT", "TODO", "TBD", "PLACEHOLDER",
        "I cannot", "I can't", "I'm unable", "As an AI"
    ],
    "max_field_lengths": {
        "study_title": 200,
        "study_object": 150,
        "study_purpose": 100,
        "key_risks": 150,
        "study_duration": 50
    }
}

# API configuration
API_CONFIG = {
    "cors_origins": os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    "rate_limit": {
        "requests_per_minute": 60,
        "requests_per_hour": 1000
    },
    "timeout_seconds": 30
}

# Logging configuration
LOGGING_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "app.log",
    "max_bytes": 10485760,  # 10MB
    "backup_count": 5
}

# Test configuration
TEST_CONFIG = {
    "default_pdf": "HUM00173014.pdf",
    "consistency_runs": 3,
    "timeout_seconds": 60
}

# Template configuration
TEMPLATE_CONFIG = {
    "template_dir": str(APP_DIR / "templates"),
    "cache_templates": os.getenv("CACHE_TEMPLATES", "true").lower() == "true"
}

# Plugin configuration
PLUGIN_CONFIG = {
    "plugin_dir": str(APP_DIR / "plugins"),
    "auto_discover": True
}

# Monitoring configuration
MONITORING_CONFIG = {
    "enabled": os.getenv("MONITORING_ENABLED", "true").lower() == "true",
    "metrics_endpoint": "/metrics/",
    "health_endpoint": "/health/"
}

# Cache configuration
CACHE_CONFIG = {
    "enabled": os.getenv("LLM_CACHE_ENABLED", "true").lower() == "true",
    "ttl_seconds": int(os.getenv("LLM_CACHE_TTL", "3600")),  # 1 hour
    "max_size": int(os.getenv("LLM_CACHE_MAX_SIZE", "1000"))
}


def get_azure_config() -> Dict[str, Any]:
    """Get Azure OpenAI configuration"""
    return AZURE_OPENAI_CONFIG


def get_cors_origins() -> List[str]:
    """Get CORS allowed origins"""
    return API_CONFIG["cors_origins"]


def get_test_pdf_path() -> Path:
    """Get default test PDF path"""
    return TEST_DATA_DIR / TEST_CONFIG["default_pdf"]


def get_log_level() -> str:
    """Get logging level"""
    return LOGGING_CONFIG["level"]


def get_template_dir() -> Path:
    """Get template directory path"""
    return Path(TEMPLATE_CONFIG["template_dir"])


def get_plugin_dir() -> Path:
    """Get plugin directory path"""
    return Path(PLUGIN_CONFIG["plugin_dir"])


def validate_config() -> bool:
    """
    Validate that required configuration is present.
    
    Returns:
        True if all required config is valid
        
    Raises:
        ValueError: If required config is missing
    """
    errors = []
    
    # Check required Azure OpenAI settings
    if not AZURE_OPENAI_CONFIG.get("api_key"):
        errors.append("Missing OPENAI_API_KEY environment variable")
    
    if not AZURE_OPENAI_CONFIG.get("endpoint"):
        errors.append("Missing OPENAI_API_BASE environment variable")
    
    # Check paths exist
    if not APP_DIR.exists():
        errors.append(f"App directory not found: {APP_DIR}")
    
    if errors:
        error_msg = "Configuration errors:\n" + "\n".join(errors)
        raise ValueError(error_msg)
    
    return True


class AppConfig:
    """Centralized application configuration."""

    # Server
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "8000"))

    # CORS
    CORS_ORIGINS = API_CONFIG["cors_origins"]
    CORS_CREDENTIALS = os.getenv("CORS_CREDENTIALS", "true").lower() == "true"
    CORS_HEADERS = ["*"]
    CORS_METHODS = ["*"]

    # Logging
    LOG_LEVEL = LOGGING_CONFIG["level"]
    LOG_FILE = LOGGING_CONFIG["file"]

    # Document Processing
    MAX_PDF_SIZE_MB = int(os.getenv("MAX_PDF_SIZE_MB", "10"))
    PROCESSING_TIMEOUT = int(os.getenv("PROCESSING_TIMEOUT", "60"))

    # Azure OpenAI
    AZURE_CONFIG = AZURE_OPENAI_CONFIG

    # Paths
    BASE_DIR = BASE_DIR
    APP_DIR = APP_DIR
    TEST_DATA_DIR = TEST_DATA_DIR
    TEMPLATE_DIR = get_template_dir()
    PLUGIN_DIR = get_plugin_dir()

    @classmethod
    def validate(cls):
        """Validate configuration on startup."""
        return validate_config()


# Export commonly used values directly
__all__ = [
    'BASE_DIR',
    'APP_DIR',
    'TEST_DATA_DIR',
    'AZURE_OPENAI_CONFIG',
    'TEXT_PROCESSING',
    'VALIDATION_CONFIG',
    'API_CONFIG',
    'LOGGING_CONFIG',
    'TEST_CONFIG',
    'TEMPLATE_CONFIG',
    'PLUGIN_CONFIG',
    'MONITORING_CONFIG',
    'CACHE_CONFIG',
    'AppConfig',
    'get_azure_config',
    'get_cors_origins',
    'get_test_pdf_path',
    'get_log_level',
    'get_template_dir',
    'get_plugin_dir',
    'validate_config'
]