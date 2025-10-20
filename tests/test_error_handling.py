"""
Tests for error handling across the application.
Ensures errors are properly raised and handled.
"""
import pytest
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.exceptions import (
    ExtractionError,
    PluginExecutionError,
    DocumentFrameworkError,
    TemplateError,
    ValidationError
)
from app.core.document_processor import SimpleDocumentProcessor
from app.core.unified_extractor import UnifiedExtractor
from app.core.extraction_models import KIExtractionSchema


class TestExtractionErrors:
    """Test extraction error handling"""

    def test_empty_document_handled_gracefully(self):
        """Test that empty documents are handled (offline mode provides defaults)"""
        processor = SimpleDocumentProcessor()

        # In offline mode, this should succeed with defaults
        import asyncio
        result = asyncio.run(processor.process(
            document_text="",
            document_type="informed-consent",
            output_schema=KIExtractionSchema
        ))

        # Should have extracted values (defaults in offline mode)
        assert result.extracted_values is not None
        assert isinstance(result.extracted_values, dict)

    def test_processor_returns_context(self):
        """Test that processor returns ProcessingContext"""
        processor = SimpleDocumentProcessor()

        import asyncio
        result = asyncio.run(processor.process(
            document_text="Test document about a research study",
            document_type="informed-consent",
            output_schema=KIExtractionSchema
        ))

        # Should return ProcessingContext with required fields
        assert hasattr(result, 'extracted_values')
        assert hasattr(result, 'document_text')
        assert hasattr(result, 'document_type')


class TestPluginErrors:
    """Test plugin execution error handling"""

    def test_plugin_execution_error_structure(self):
        """Test PluginExecutionError has proper structure"""
        error = PluginExecutionError(
            plugin_id="test-plugin",
            message="Test failure",
            details={"reason": "test"}
        )

        assert error.plugin_id == "test-plugin"
        assert "test-plugin" in str(error)
        assert error.details["reason"] == "test"


class TestValidationErrors:
    """Test validation error handling"""

    def test_validation_error_structure(self):
        """Test ValidationError has proper field information"""
        error = ValidationError(
            field="study_title",
            message="Field is required",
            value=None
        )

        assert error.field == "study_title"
        assert "study_title" in str(error)


class TestDocumentFrameworkErrors:
    """Test framework-level error handling"""

    def test_framework_error_with_details(self):
        """Test DocumentFrameworkError includes context details"""
        error = DocumentFrameworkError(
            "Processing failed",
            {"document_type": "test", "step": "extraction"}
        )

        assert error.message == "Processing failed"
        assert error.details["document_type"] == "test"
        assert error.details["step"] == "extraction"

    def test_template_error_structure(self):
        """Test TemplateError has template path"""
        error = TemplateError(
            template_path="test.j2",
            message="Template not found"
        )

        assert error.template_path == "test.j2"
        assert "test.j2" in str(error)


class TestErrorPropagation:
    """Test that errors propagate correctly through the stack"""

    def test_extraction_error_preserves_context(self):
        """Test that extraction errors preserve context information"""
        error = ExtractionError(
            "JSON parsing failed",
            {"json_snippet": '{"invalid": '}
        )

        assert "JSON parsing failed" in str(error)
        assert "json_snippet" in error.details


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
