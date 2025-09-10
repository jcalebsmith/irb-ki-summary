"""
Configuration settings for the IRB KI Summary application.
Centralizes all hardcoded values for easier maintenance.
"""

import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).parent.parent
APP_DIR = BASE_DIR / "app"
TEST_DATA_DIR = BASE_DIR / "test_data"

# Load environment variables from app/.env
env_path = APP_DIR / '.env'
load_dotenv(env_path, override=True)

# Memory system configuration
MEMORY_CONFIG = {
    "max_entities": 5000,
    "max_episodes": 1000,
    "max_observations_per_entity": 100,
    "max_memory_size_mb": 10,
    "decay_lambda": 0.1,
    "decay_enabled": True,
    "confidence_threshold": 0.5,
    "relevance_threshold": 0.3,
}

# Token and text processing limits
TEXT_PROCESSING = {
    "max_tokens_per_batch": 18000,
    "truncation_limits": {
        "short": 150,
        "medium": 200,
        "long": 4000,
        "extra_long": 8000
    },
    "chunk_size": 2000,  # Default chunk size for text processing
    "extraction_context_limits": {
        "first_pass": 12000,  # Context limit for first extraction pass
        "second_pass": 15000,  # Extended context for second pass
    }
}

# Test data configuration
TEST_CONFIG = {
    "default_test_pdf": "HUM00173014.pdf",
    "test_data_path": str(TEST_DATA_DIR),
    "consistency_test_runs": 3,
    "cv_target_threshold": 15.0,  # Coefficient of variation target < 15%
}

# Azure OpenAI configuration - centralized environment variable access
AZURE_OPENAI_CONFIG = {
    "api_key": os.getenv("OPENAI_API_KEY"),
    "endpoint": os.getenv("OPENAI_API_BASE"),
    "api_version": os.getenv("API_VERSION", "2024-10-21"),
    "organization": os.getenv("ORGANIZATION", "231173"),
    "deployment_llm": os.getenv("AZURE_OPENAI_DEPLOYMENT_LLM"),
    "deployment_embedding": os.getenv("AZURE_OPENAI_DEPLOYMENT_EMBEDDING", "text-embedding-3-small"),
    "temperature": 0.1,
    "default_headers": {
        "OpenAI-Organization": os.getenv("ORGANIZATION", "231173"),
        "Shortcode": os.getenv("ORGANIZATION", "231173")
    },
    "llm_model": "gpt-4o",
    "embedding_model": "text-embedding-3-small",
}

# CORS configuration
CORS_CONFIG = {
    "allow_origins": os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["*"],
}

# Validation constants
VALIDATION_CONFIG = {
    "prohibited_phrases": [
        "[INSERT", "TODO", "TBD", "PLACEHOLDER",
        "[EXTRACTED", "[YOUR", "[COMPANY", 
        "{{", "}}", "{%", "%}"
    ],
    "critical_value_patterns": [
        r"\d+\s*(?:days?|weeks?|months?|years?)",
        r"\$[\d,]+(?:\.\d{2})?",
        r"\d+\s*(?:mg|ml|mcg|units?)",
        r"\d+:\d+\s*(?:am|pm|AM|PM)",
    ],
}

# API rate limiting
RATE_LIMIT_CONFIG = {
    "requests_per_minute": 60,
    "requests_per_hour": 1000,
    "burst_size": 10,
}

# Logging configuration
LOGGING_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "app.log",
    "max_bytes": 10485760,  # 10MB
    "backup_count": 5,
}

def get_config() -> Dict[str, Any]:
    """Get complete configuration dictionary."""
    return {
        "memory": MEMORY_CONFIG,
        "text_processing": TEXT_PROCESSING,
        "test": TEST_CONFIG,
        "azure_openai": AZURE_OPENAI_CONFIG,
        "cors": CORS_CONFIG,
        "validation": VALIDATION_CONFIG,
        "rate_limit": RATE_LIMIT_CONFIG,
        "logging": LOGGING_CONFIG,
        "paths": {
            "base_dir": str(BASE_DIR),
            "app_dir": str(APP_DIR),
            "test_data_dir": str(TEST_DATA_DIR),
        }
    }

def get_test_pdf_path() -> Path:
    """Get the default test PDF path."""
    return TEST_DATA_DIR / TEST_CONFIG["default_test_pdf"]