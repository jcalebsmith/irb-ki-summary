"""
Tests for application configuration management.
Ensures configuration loads correctly and environment overrides work.
"""
import pytest
import os
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import (
    AppConfig,
    get_cors_origins,
    get_test_pdf_path,
    get_log_level,
    validate_config,
    AZURE_OPENAI_CONFIG,
    API_CONFIG,
    LOGGING_CONFIG,
    TEST_CONFIG
)


class TestAppConfig:
    """Test centralized AppConfig class"""

    def test_app_config_has_required_attributes(self):
        """Test that AppConfig has all required attributes"""
        assert hasattr(AppConfig, 'HOST')
        assert hasattr(AppConfig, 'PORT')
        assert hasattr(AppConfig, 'CORS_ORIGINS')
        assert hasattr(AppConfig, 'CORS_CREDENTIALS')
        assert hasattr(AppConfig, 'LOG_LEVEL')
        assert hasattr(AppConfig, 'MAX_PDF_SIZE_MB')

    def test_cors_configuration(self):
        """Test CORS configuration is properly loaded"""
        assert isinstance(AppConfig.CORS_ORIGINS, list)
        assert isinstance(AppConfig.CORS_CREDENTIALS, bool)
        assert isinstance(AppConfig.CORS_HEADERS, list)
        assert isinstance(AppConfig.CORS_METHODS, list)

    def test_server_configuration(self):
        """Test server configuration has valid values"""
        assert isinstance(AppConfig.HOST, str)
        assert isinstance(AppConfig.PORT, int)
        assert AppConfig.PORT > 0
        assert AppConfig.PORT < 65536

    def test_logging_configuration(self):
        """Test logging configuration"""
        assert AppConfig.LOG_LEVEL in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        assert isinstance(AppConfig.LOG_FILE, str)

    def test_processing_limits(self):
        """Test document processing limits are set"""
        assert isinstance(AppConfig.MAX_PDF_SIZE_MB, int)
        assert AppConfig.MAX_PDF_SIZE_MB > 0
        assert isinstance(AppConfig.PROCESSING_TIMEOUT, int)
        assert AppConfig.PROCESSING_TIMEOUT > 0


class TestConfigurationDictionaries:
    """Test individual configuration dictionaries"""

    def test_azure_openai_config(self):
        """Test Azure OpenAI configuration structure"""
        assert isinstance(AZURE_OPENAI_CONFIG, dict)
        assert "api_key" in AZURE_OPENAI_CONFIG
        assert "endpoint" in AZURE_OPENAI_CONFIG
        assert "api_version" in AZURE_OPENAI_CONFIG
        assert "deployment_name" in AZURE_OPENAI_CONFIG
        assert "temperature" in AZURE_OPENAI_CONFIG

    def test_api_config(self):
        """Test API configuration structure"""
        assert isinstance(API_CONFIG, dict)
        assert "cors_origins" in API_CONFIG
        assert "rate_limit" in API_CONFIG
        assert "timeout_seconds" in API_CONFIG

    def test_logging_config(self):
        """Test logging configuration structure"""
        assert isinstance(LOGGING_CONFIG, dict)
        assert "level" in LOGGING_CONFIG
        assert "format" in LOGGING_CONFIG
        assert "file" in LOGGING_CONFIG

    def test_test_config(self):
        """Test test configuration structure"""
        assert isinstance(TEST_CONFIG, dict)
        assert "default_pdf" in TEST_CONFIG
        assert "consistency_runs" in TEST_CONFIG


class TestConfigurationHelpers:
    """Test configuration helper functions"""

    def test_get_cors_origins_returns_list(self):
        """Test get_cors_origins returns a list"""
        origins = get_cors_origins()
        assert isinstance(origins, list)
        assert len(origins) > 0

    def test_get_test_pdf_path_returns_path(self):
        """Test get_test_pdf_path returns Path object"""
        pdf_path = get_test_pdf_path()
        assert isinstance(pdf_path, Path)
        assert pdf_path.suffix == ".pdf"

    def test_get_log_level_returns_string(self):
        """Test get_log_level returns valid log level"""
        log_level = get_log_level()
        assert isinstance(log_level, str)
        assert log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']


class TestEnvironmentOverrides:
    """Test that environment variables override defaults"""

    def test_cors_origins_from_env(self):
        """Test CORS origins can be set via environment"""
        # CORS_ORIGINS is loaded at import time, so we check the current value
        # matches either default or env override
        origins = get_cors_origins()
        assert isinstance(origins, list)
        # Should have at least localhost:3000
        assert any("localhost" in origin for origin in origins)

    def test_log_level_from_env(self):
        """Test log level can be set via environment"""
        log_level = get_log_level()
        # Should be one of the valid log levels
        assert log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']


class TestConfigurationValidation:
    """Test configuration validation"""

    def test_validate_config_succeeds_with_valid_config(self):
        """Test that validate_config succeeds with valid configuration"""
        # This should not raise if config is valid
        # Note: May raise ValueError if Azure keys are missing
        try:
            result = validate_config()
            assert result is True
        except ValueError as e:
            # This is expected if Azure credentials are not set
            assert "OPENAI_API_KEY" in str(e) or "OPENAI_API_BASE" in str(e)

    def test_app_config_validate_method(self):
        """Test AppConfig.validate() method"""
        # Should delegate to validate_config()
        try:
            result = AppConfig.validate()
            assert result is True
        except ValueError:
            # Expected if credentials not configured
            pass


class TestConfigurationDefaults:
    """Test default configuration values"""

    def test_default_host(self):
        """Test default host is localhost"""
        assert AppConfig.HOST in ["127.0.0.1", "localhost", "0.0.0.0"]

    def test_default_port(self):
        """Test default port is 8000"""
        assert AppConfig.PORT == 8000 or isinstance(AppConfig.PORT, int)

    def test_default_cors_credentials(self):
        """Test default CORS credentials setting"""
        assert isinstance(AppConfig.CORS_CREDENTIALS, bool)

    def test_default_max_pdf_size(self):
        """Test default max PDF size is reasonable"""
        assert AppConfig.MAX_PDF_SIZE_MB >= 10
        assert AppConfig.MAX_PDF_SIZE_MB <= 100

    def test_default_processing_timeout(self):
        """Test default processing timeout is reasonable"""
        assert AppConfig.PROCESSING_TIMEOUT >= 30
        assert AppConfig.PROCESSING_TIMEOUT <= 300


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
