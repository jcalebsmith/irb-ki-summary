"""
Type definitions for the Document Generation Framework.

This module provides clear type definitions to improve code readability
and help junior developers understand data structures used throughout
the application.
"""

from typing import TypedDict, List, Dict, Any, Optional, Literal
from dataclasses import dataclass
from enum import Enum


# Validation-related types
class ValidationResult(TypedDict):
    """Structure for validation results returned by validators."""
    passed: bool
    issues: List[str]
    warnings: List[str]
    info: List[str]
    consistency_metrics: Dict[str, float]
    content_analysis: Dict[str, Any]


class ConsistencyThresholds(TypedDict):
    """Thresholds for consistency validation."""
    coefficient_of_variation: float  # Target: < 15%
    structural_score: float  # Target: > 0.8
    min_sentences: int  # Minimum sentences required
    max_cv_tolerance: float  # Maximum CV tolerance


# Extraction-related types
class ExtractionField(TypedDict):
    """Definition of a field to extract from documents."""
    type: Literal["boolean", "enum", "text", "numeric"]
    description: str
    options: Optional[List[str]]  # For enum types
    max_words: Optional[int]  # For text types
    required: bool
    default_value: Optional[Any]


class ExtractionResult(TypedDict):
    """Result from document extraction process."""
    field_name: str
    value: Any
    confidence: float
    source_page: Optional[int]
    source_text: Optional[str]


# Document processing types
class DocumentMetadata(TypedDict):
    """Metadata associated with a processed document."""
    filename: str
    page_count: int
    processing_time: float
    document_type: str
    template_used: Optional[str]


class SectionContent(TypedDict):
    """Content for a single section of generated document."""
    section_number: int
    section_title: str
    content: str
    word_count: int
    extracted_values: Dict[str, Any]


# Plugin-related types
class PluginInfo(TypedDict):
    """Information about a loaded plugin."""
    name: str
    version: str
    supported_document_types: List[str]
    description: str
    author: Optional[str]
    template_count: int


# Agent communication types
class AgentTaskRequest(TypedDict):
    """Request sent to an agent for processing."""
    task_type: str
    document_text: str
    parameters: Dict[str, Any]
    priority: Literal["low", "medium", "high"]
    timeout_seconds: Optional[int]


class AgentTaskResponse(TypedDict):
    """Response from an agent after processing."""
    success: bool
    result: Any
    error_message: Optional[str]
    processing_time: float
    agent_name: str


# Template-related types
class TemplateSlotDefinition(TypedDict):
    """Definition of a template slot for content generation."""
    name: str
    slot_type: Literal["static", "extracted", "generated", "conditional", "propagated"]
    extraction_query: str
    validation_rules: Dict[str, Any]
    default_value: Optional[str]
    max_length: Optional[int]
    is_critical: bool  # If true, value must be preserved exactly


class TemplateContext(TypedDict):
    """Context provided to template engine for rendering."""
    document_type: str
    extracted_values: Dict[str, Any]
    generated_content: Dict[str, str]
    metadata: DocumentMetadata
    user_parameters: Dict[str, Any]


# Configuration constants (extracted from magic numbers/strings)
class ValidationConstants:
    """Constants used for validation throughout the framework."""
    
    # Consistency thresholds
    TARGET_CV_PERCENTAGE = 15.0  # Target coefficient of variation
    MIN_STRUCTURAL_SCORE = 0.8  # Minimum structural consistency score
    
    # Content limits
    DEFAULT_MAX_WORDS = 30
    MIN_SENTENCE_COUNT = 3
    MAX_SENTENCE_COUNT = 100
    
    # Validation messages
    MISSING_REQUIRED_FIELD = "Required field '{}' is missing"
    EXCEEDS_LENGTH_LIMIT = "Field '{}' exceeds maximum length of {} characters"
    INVALID_ENUM_VALUE = "Field '{}' has invalid value. Must be one of: {}"
    
    # Prohibited phrases that indicate AI-generated artifacts
    PROHIBITED_PHRASES = [
        "As an AI", "I cannot", "I don't have access",
        "Based on the document", "According to the text",
        "The document states", "It appears that",
        "<<", ">>", "[[", "]]",  # Template artifacts
        "PLACEHOLDER", "TODO", "TBD",
        "In summary,", "To summarize,", "In conclusion,"
    ]


class ProcessingConstants:
    """Constants for document processing."""
    
    # Chunk sizes for RAG pipeline
    DEFAULT_CHUNK_SIZE = 1024
    DEFAULT_CHUNK_OVERLAP = 128
    
    # Timeouts
    AGENT_TIMEOUT_SECONDS = 30
    EXTRACTION_TIMEOUT_SECONDS = 60
    GENERATION_TIMEOUT_SECONDS = 120
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 2
    
    # Concurrency limits
    MAX_CONCURRENT_EXTRACTIONS = 5
    MAX_CONCURRENT_GENERATIONS = 3


@dataclass
class ProcessingError(Exception):
    """Custom exception for document processing errors."""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    
    def __str__(self):
        return f"[{self.error_code}] {self.message}"


# Error codes for better error handling
class ErrorCodes:
    """Standardized error codes for the framework."""
    
    # Document errors
    DOC_INVALID_FORMAT = "DOC001"
    DOC_PARSE_FAILED = "DOC002"
    DOC_TOO_LARGE = "DOC003"
    
    # Extraction errors
    EXT_FIELD_NOT_FOUND = "EXT001"
    EXT_TIMEOUT = "EXT002"
    EXT_LLM_ERROR = "EXT003"
    
    # Generation errors
    GEN_TEMPLATE_ERROR = "GEN001"
    GEN_VALIDATION_FAILED = "GEN002"
    GEN_TIMEOUT = "GEN003"
    
    # Plugin errors
    PLG_NOT_FOUND = "PLG001"
    PLG_LOAD_FAILED = "PLG002"
    PLG_INVALID_CONFIG = "PLG003"