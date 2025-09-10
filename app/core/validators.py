"""
Modular validators for the document generation framework.

This module provides focused validator classes following the Single Responsibility Principle,
replacing the monolithic EnhancedValidationOrchestrator.
"""

from typing import Dict, Any, List, Optional, Set
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import re
import hashlib
import numpy as np
from collections import defaultdict

from .exceptions import ValidationError
from .plugin_manager import ValidationRuleSet
from .types import ValidationResult, ConsistencyThresholds


@dataclass
class ValidationContext:
    """Context passed between validators."""
    original: dict[str, Any]
    rendered: str
    rules: ValidationRuleSet
    critical_values: list[str]
    document_type: str = "default"
    results: dict[str, Any] = field(default_factory=lambda: {
        "passed": True,
        "issues": [],
        "warnings": [],
        "info": [],
        "consistency_metrics": {},
        "content_analysis": {}
    })


class BaseValidator(ABC):
    """Abstract base class for all validators."""
    
    @abstractmethod
    def validate(self, context: ValidationContext) -> ValidationContext:
        """
        Perform validation and update context results.
        
        Args:
            context: Validation context with data and rules
            
        Returns:
            Updated validation context
        """
        pass
    
    def add_issue(self, context: ValidationContext, message: str) -> None:
        """Add an issue and mark validation as failed."""
        context.results["issues"].append(message)
        context.results["passed"] = False
    
    def add_warning(self, context: ValidationContext, message: str) -> None:
        """Add a warning without failing validation."""
        context.results["warnings"].append(message)
    
    def add_info(self, context: ValidationContext, message: str) -> None:
        """Add informational message."""
        context.results["info"].append(message)


class FieldValidator(BaseValidator):
    """Validates field-level requirements."""
    
    def validate(self, context: ValidationContext) -> ValidationContext:
        """Validate required fields, lengths, and allowed values."""
        self._validate_required_fields(context)
        self._validate_field_lengths(context)
        self._validate_allowed_values(context)
        return context
    
    def _validate_required_fields(self, context: ValidationContext) -> None:
        """Check that all required fields are present."""
        for field in context.rules.required_fields:
            if field not in context.original or not context.original[field]:
                self.add_issue(context, f"Required field missing: {field}")
    
    def _validate_field_lengths(self, context: ValidationContext) -> None:
        """Check field lengths against maximum limits."""
        for field, max_length in context.rules.max_lengths.items():
            if field in context.original:
                field_length = len(str(context.original[field]))
                if field_length > max_length:
                    self.add_warning(
                        context,
                        f"Field {field} exceeds max length: {field_length} > {max_length}"
                    )
    
    def _validate_allowed_values(self, context: ValidationContext) -> None:
        """Check fields contain only allowed values."""
        # Ensure we're working with a dict
        original = context.original
        if not isinstance(original, dict):
            if hasattr(original, '__dict__'):
                original = vars(original)
            else:
                self.add_issue(context, f"Cannot validate: original is {type(original)}, not dict")
                return
        
        for field, allowed in context.rules.allowed_values.items():
            if field in original:
                value = original[field]
                if value not in allowed:
                    self.add_issue(
                        context,
                        f"Field {field} has invalid value: '{value}' not in {allowed}"
                    )


class ContentQualityValidator(BaseValidator):
    """Validates content quality and structure."""
    
    # Default prohibited phrases that indicate LLM artifacts
    PROHIBITED_PHRASES = [
        "I cannot", "I can't", "I'm unable", "As an AI", "As a language model",
        "I don't have access", "I am not able", "My training data",
        "I'm designed to", "Hello!", "Hi there!", "Greetings!",
        "Is there anything else", "Feel free to ask", "How can I help",
        "Let me know if", "I hope this helps", "Please note that"
    ]
    
    def __init__(self, prohibited_phrases: Optional[list[str]] = None):
        """Initialize with optional custom prohibited phrases."""
        self.prohibited_phrases = prohibited_phrases or self.PROHIBITED_PHRASES
    
    def validate(self, context: ValidationContext) -> ValidationContext:
        """Check content quality including prohibited phrases and sentence structure."""
        self._check_prohibited_phrases(context)
        self._check_sentence_quality(context)
        self._analyze_content_metrics(context)
        return context
    
    def _check_prohibited_phrases(self, context: ValidationContext) -> None:
        """Check for prohibited phrases that indicate LLM artifacts."""
        found_phrases = []
        rendered_lower = context.rendered.lower()
        
        for phrase in self.prohibited_phrases:
            if phrase.lower() in rendered_lower:
                found_phrases.append(phrase)
        
        if found_phrases:
            self.add_issue(context, f"Prohibited phrases found: {', '.join(found_phrases)}")
    
    def _check_sentence_quality(self, context: ValidationContext) -> None:
        """Check sentence structure and quality."""
        sentences = re.split(r'[.!?]+', context.rendered)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        issues: Set[str] = set()
        
        for sentence in sentences:
            # Check for sentences starting with lowercase
            if sentence and not sentence[0].isupper() and not sentence[0].isdigit():
                issues.add("Sentence starting with lowercase")
            
            # Check for very short sentences (likely fragments)
            word_count = len(sentence.split())
            if word_count < 3:
                issues.add("Very short sentence fragment")
            
            # Check for very long sentences
            if word_count > 50:
                issues.add("Excessively long sentence")
        
        # Add unique issues as warnings (limit to 3)
        for issue in list(issues)[:3]:
            self.add_warning(context, issue)
        
        context.results["content_analysis"]["sentence_count"] = len(sentences)
    
    def _analyze_content_metrics(self, context: ValidationContext) -> None:
        """Analyze basic content metrics."""
        word_count = len(context.rendered.split())
        char_count = len(context.rendered)
        
        context.results["content_analysis"]["word_count"] = word_count
        context.results["content_analysis"]["character_count"] = char_count


class StructuralValidator(BaseValidator):
    """Validates document structure and formatting."""
    
    def __init__(self, expected_sections: int = 9):
        """Initialize with expected number of sections."""
        self.expected_sections = expected_sections
    
    def validate(self, context: ValidationContext) -> ValidationContext:
        """Check structural consistency of the document."""
        self._check_section_structure(context)
        self._check_paragraph_consistency(context)
        return context
    
    def _check_section_structure(self, context: ValidationContext) -> None:
        """Check for consistent section markers."""
        sections = re.findall(r'^Section \d+', context.rendered, re.MULTILINE)
        
        if sections:
            unique_sections = len(set(sections))
            if unique_sections != self.expected_sections:
                self.add_warning(
                    context,
                    f"Section count mismatch: found {unique_sections}, "
                    f"expected {self.expected_sections}"
                )
    
    def _check_paragraph_consistency(self, context: ValidationContext) -> None:
        """Check paragraph structure consistency."""
        paragraphs = context.rendered.split('\n\n')
        paragraph_lengths = [len(p.split()) for p in paragraphs if p.strip()]
        
        if paragraph_lengths:
            avg_length = np.mean(paragraph_lengths)
            std_length = np.std(paragraph_lengths)
            cv = (std_length / avg_length * 100) if avg_length > 0 else 0
            
            context.results["content_analysis"]["paragraph_cv"] = cv
            if cv > 50:  # High variability
                self.add_info(context, f"High paragraph length variability: CV={cv:.1f}%")


class CriticalValueValidator(BaseValidator):
    """Validates preservation of critical values."""
    
    def validate(self, context: ValidationContext) -> ValidationContext:
        """Ensure critical values are preserved in the output."""
        preserved = 0
        total = 0
        
        for critical_field in context.critical_values:
            if critical_field in context.original:
                total += 1
                critical_value = str(context.original[critical_field])
                if critical_value in context.rendered:
                    preserved += 1
                else:
                    self.add_issue(
                        context,
                        f"Critical value '{critical_value}' for field '{critical_field}' "
                        f"not preserved"
                    )
        
        if total > 0:
            preservation_rate = preserved / total
            context.results["content_analysis"]["critical_value_preservation"] = preservation_rate
            
            if preservation_rate < 1.0:
                self.add_warning(
                    context,
                    f"Critical value preservation rate: {preservation_rate:.1%}"
                )
        
        return context


@dataclass
class ConsistencyMetrics:
    """Track consistency metrics across multiple runs."""
    word_counts: list[int] = field(default_factory=list)
    sentence_counts: list[int] = field(default_factory=list)
    content_hashes: list[str] = field(default_factory=list)
    
    def calculate_coefficient_of_variation(self) -> float:
        """Calculate coefficient of variation for word counts."""
        if len(self.word_counts) < 2:
            return 0.0
        mean_count = np.mean(self.word_counts)
        if mean_count == 0:
            return 0.0
        std_count = np.std(self.word_counts)
        return (std_count / mean_count) * 100
    
    def calculate_structural_consistency(self) -> float:
        """Calculate structural consistency based on content hashes."""
        if len(self.content_hashes) < 2:
            return 1.0
        unique_hashes = len(set(self.content_hashes))
        return 1.0 - (unique_hashes - 1) / len(self.content_hashes)


class ConsistencyTracker:
    """Tracks consistency metrics across multiple validation runs."""
    
    def __init__(self):
        """Initialize consistency tracker."""
        self.metrics_by_type = defaultdict(ConsistencyMetrics)
    
    def track(self, rendered: str, document_type: str) -> None:
        """Track metrics for consistency analysis."""
        metrics = self.metrics_by_type[document_type]
        
        # Track content hash
        content_hash = hashlib.md5(rendered.encode()).hexdigest()[:8]
        metrics.content_hashes.append(content_hash)
        
        # Track word count
        word_count = len(rendered.split())
        metrics.word_counts.append(word_count)
        
        # Track sentence count
        sentence_count = len(re.split(r'[.!?]+', rendered))
        metrics.sentence_counts.append(sentence_count)
    
    def get_metrics(self, document_type: str) -> dict[str, Any]:
        """Get consistency metrics for a document type."""
        metrics = self.metrics_by_type[document_type]
        
        if len(metrics.word_counts) < 2:
            return {
                "runs_analyzed": len(metrics.word_counts),
                "insufficient_data": True
            }
        
        cv = metrics.calculate_coefficient_of_variation()
        structural = metrics.calculate_structural_consistency()
        
        return {
            "runs_analyzed": len(metrics.word_counts),
            "coefficient_of_variation": cv,
            "structural_consistency": structural,
            "mean_word_count": np.mean(metrics.word_counts),
            "std_word_count": np.std(metrics.word_counts),
            "unique_outputs": len(set(metrics.content_hashes)),
            "target_achieved": cv < 15.0  # Target CV < 15%
        }
    
    def get_report(self, document_type: Optional[str] = None) -> dict[str, Any]:
        """Generate comprehensive consistency report."""
        report = {
            "overall_metrics": {},
            "by_document_type": {}
        }
        
        types = [document_type] if document_type else list(self.metrics_by_type.keys())
        
        for doc_type in types:
            metrics = self.metrics_by_type[doc_type]
            if len(metrics.word_counts) > 0:
                report["by_document_type"][doc_type] = {
                    "runs": len(metrics.word_counts),
                    "cv": metrics.calculate_coefficient_of_variation(),
                    "structural_consistency": metrics.calculate_structural_consistency(),
                    "mean_word_count": np.mean(metrics.word_counts),
                    "unique_outputs": len(set(metrics.content_hashes))
                }
        
        # Calculate overall metrics
        all_cvs = [m["cv"] for m in report["by_document_type"].values()]
        if all_cvs:
            report["overall_metrics"] = {
                "mean_cv": np.mean(all_cvs),
                "meets_target": all(cv < 15.0 for cv in all_cvs)
            }
        
        return report


class ValidationOrchestrator:
    """
    Orchestrates multiple validators in a pipeline.
    
    This replaces the monolithic EnhancedValidationOrchestrator with
    a modular, extensible design.
    """
    
    def __init__(self, expected_sections: int = 9):
        """
        Initialize validation orchestrator with default validators.
        
        Args:
            expected_sections: Expected number of sections in document
        """
        self.validators = [
            FieldValidator(),
            ContentQualityValidator(),
            StructuralValidator(expected_sections),
            CriticalValueValidator()
        ]
        self.consistency_tracker = ConsistencyTracker()
    
    def add_validator(self, validator: BaseValidator) -> None:
        """Add a custom validator to the pipeline."""
        self.validators.append(validator)
    
    def validate(self,
                original: dict[str, Any],
                rendered: str,
                rules: ValidationRuleSet,
                critical_values: list[str],
                document_type: str = "default") -> dict[str, Any]:
        """
        Run all validators in sequence.
        
        Args:
            original: Original extracted values
            rendered: Rendered document content
            rules: Validation rules to apply
            critical_values: Critical values that must be preserved
            document_type: Type of document being validated
            
        Returns:
            Comprehensive validation results
        """
        # Create validation context
        context = ValidationContext(
            original=original,
            rendered=rendered,
            rules=rules,
            critical_values=critical_values,
            document_type=document_type
        )
        
        # Run validators in sequence
        for validator in self.validators:
            context = validator.validate(context)
        
        # Track consistency metrics
        self.consistency_tracker.track(rendered, document_type)
        
        # Add consistency metrics to results
        context.results["consistency_metrics"] = self.consistency_tracker.get_metrics(document_type)
        
        return context.results
    
    def get_consistency_report(self, document_type: Optional[str] = None) -> dict[str, Any]:
        """
        Get consistency report across validation runs.
        
        Args:
            document_type: Optional specific document type to report on
            
        Returns:
            Comprehensive consistency report
        """
        return self.consistency_tracker.get_report(document_type)


# Backward compatibility alias
EnhancedValidationOrchestrator = ValidationOrchestrator