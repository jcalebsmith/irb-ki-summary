"""
Custom exception hierarchy for the document generation framework.

This module provides a structured exception hierarchy for better error handling
and debugging throughout the application.
"""

from typing import Optional, Any


class DocumentFrameworkError(Exception):
    """Base exception for all document framework errors."""
    
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class PluginError(DocumentFrameworkError):
    """Raised when plugin-related errors occur."""
    
    def __init__(self, plugin_id: str, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(f"Plugin '{plugin_id}' error: {message}", details)
        self.plugin_id = plugin_id


class PluginNotFoundError(PluginError):
    """Raised when a requested plugin cannot be found."""
    
    def __init__(self, plugin_id: str):
        super().__init__(plugin_id, f"Plugin '{plugin_id}' not found")


class PluginLoadError(PluginError):
    """Raised when a plugin fails to load."""
    
    def __init__(self, plugin_id: str, reason: str):
        super().__init__(plugin_id, f"Failed to load: {reason}")


class ValidationError(DocumentFrameworkError):
    """Raised when validation fails."""
    
    def __init__(self, field: str, message: str, value: Any = None):
        details = {"field": field}
        if value is not None:
            details["value"] = value
        super().__init__(f"Validation error for '{field}': {message}", details)
        self.field = field
        self.value = value


class TemplateError(DocumentFrameworkError):
    """Raised when template-related errors occur."""
    
    def __init__(self, template_path: str, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(f"Template '{template_path}' error: {message}", details)
        self.template_path = template_path


class TemplateNotFoundError(TemplateError):
    """Raised when a template file cannot be found."""
    
    def __init__(self, template_path: str):
        super().__init__(template_path, "Template file not found")


class TemplateRenderError(TemplateError):
    """Raised when template rendering fails."""
    
    def __init__(self, template_path: str, reason: str):
        super().__init__(template_path, f"Rendering failed: {reason}")


class ExtractionError(DocumentFrameworkError):
    """Raised when document extraction fails."""
    
    def __init__(self, message: str, document_type: Optional[str] = None, details: Optional[dict[str, Any]] = None):
        if details is None:
            details = {}
        if document_type:
            details["document_type"] = document_type
        super().__init__(message, details)
        self.document_type = document_type


class LLMError(DocumentFrameworkError):
    """Raised when LLM operations fail."""
    
    def __init__(self, operation: str, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(f"LLM {operation} failed: {message}", details)
        self.operation = operation


class AgentError(DocumentFrameworkError):
    """Raised when agent operations fail."""
    
    def __init__(self, agent_name: str, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(f"Agent '{agent_name}' error: {message}", details)
        self.agent_name = agent_name


class AgentCommunicationError(AgentError):
    """Raised when agents fail to communicate properly."""
    
    def __init__(self, sender: str, receiver: str, message: str):
        super().__init__(
            sender, 
            f"Communication with '{receiver}' failed: {message}",
            {"sender": sender, "receiver": receiver}
        )
        self.sender = sender
        self.receiver = receiver


class ConfigurationError(DocumentFrameworkError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, config_key: str, message: str):
        super().__init__(f"Configuration error for '{config_key}': {message}", {"config_key": config_key})
        self.config_key = config_key


class PDFProcessingError(DocumentFrameworkError):
    """Raised when PDF processing fails."""
    
    def __init__(self, filename: str, message: str, page: Optional[int] = None):
        details = {"filename": filename}
        if page is not None:
            details["page"] = page
        super().__init__(f"PDF processing error in '{filename}': {message}", details)
        self.filename = filename
        self.page = page


