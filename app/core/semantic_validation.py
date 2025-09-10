"""
Semantic validation and self-healing pipeline for IRB document extraction
Provides multi-layer validation with confidence scoring and automatic correction
"""

import re
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum
import asyncio
from pydantic import BaseModel
from app.logger import get_logger
from app.core.extraction_models import (
    KIExtractionSchema, 
    StudyType, 
    PopulationType,
    ClinicalProtocolExtractionSchema
)
from app.core.exceptions import ValidationError, ExtractionError

logger = get_logger("core.semantic_validation")

# Single config constant - KISS principle
CONFIDENCE_THRESHOLD = 0.7  # One number to tune, not 20


class ConfidenceLevel(Enum):
    """Confidence levels for extracted fields"""
    HIGH = "high"      # > 0.9 - No concerns
    MEDIUM = "medium"  # 0.7-0.9 - Minor concerns
    LOW = "low"        # 0.5-0.7 - Needs review
    CRITICAL = "critical"  # < 0.5 - Must re-extract


@dataclass
class FieldValidationResult:
    """Validation result for a single field"""
    field_name: str
    value: Any
    is_valid: bool
    confidence: float
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    needs_reextraction: bool = False
    refined_value: Optional[Any] = None
    
    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Get confidence level category"""
        if self.confidence > 0.9:
            return ConfidenceLevel.HIGH
        elif self.confidence > 0.7:
            return ConfidenceLevel.MEDIUM
        elif self.confidence > 0.5:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.CRITICAL


@dataclass
class DocumentValidationResult:
    """Complete validation result for a document"""
    is_valid: bool
    overall_confidence: float
    field_results: Dict[str, FieldValidationResult]
    cross_field_issues: List[str] = field(default_factory=list)
    requires_human_review: bool = False
    extraction_attempts: int = 1
    
    def get_problematic_fields(self) -> List[str]:
        """Get list of fields needing attention"""
        return [
            name for name, result in self.field_results.items()
            if result.confidence < 0.7 or not result.is_valid
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "is_valid": self.is_valid,
            "overall_confidence": self.overall_confidence,
            "requires_human_review": self.requires_human_review,
            "field_results": {
                name: {
                    "value": str(result.value),
                    "confidence": result.confidence,
                    "is_valid": result.is_valid,
                    "issues": result.issues
                }
                for name, result in self.field_results.items()
            },
            "cross_field_issues": self.cross_field_issues
        }


class SemanticFieldValidator:
    """
    Validates individual fields for semantic correctness
    Specific to IRB Key Information summaries
    """
    
    def __init__(self):
        """Initialize semantic validator with domain rules"""
        # Duration patterns and valid ranges
        self.duration_pattern = re.compile(
            r'(\d+(?:\.\d+)?)\s*(day|week|month|year|hour|minute|visit|cycle)s?',
            re.IGNORECASE
        )
        
        # Valid duration ranges in days
        self.duration_ranges = {
            "min_days": 1,
            "max_days": 3650,  # 10 years
            "typical_min": 7,   # 1 week
            "typical_max": 730   # 2 years
        }
        
        # Risk keywords that should appear for different study types
        self.risk_keywords = {
            "device": ["device", "implant", "procedure", "surgery", "insertion"],
            "drug": ["medication", "side effect", "reaction", "dose", "drug"],
            "radiation": ["radiation", "x-ray", "exposure", "imaging"],
            "genetic": ["genetic", "dna", "gene", "hereditary"],
            "behavioral": ["survey", "interview", "questionnaire", "psychological"]
        }
        
        # Population consistency patterns
        self.population_patterns = {
            PopulationType.CHILDREN: ["child", "pediatric", "minor", "youth", "adolescent"],
            PopulationType.LARGE_NUMBERS_PEOPLE: ["large", "many", "multiple", "hundreds", "thousands"],
            PopulationType.SMALL_NUMBERS_PEOPLE: ["small", "few", "limited", "select"]
        }
    
    def validate_duration(self, value: str) -> FieldValidationResult:
        """
        Validate study duration field
        
        Args:
            value: Duration string to validate
            
        Returns:
            FieldValidationResult with confidence and issues
        """
        result = FieldValidationResult(
            field_name="study_duration",
            value=value,
            is_valid=True,
            confidence=1.0
        )
        
        # Check for empty or placeholder values
        if not value or value.lower() in ["", "not specified", "varies", "unknown", "tbd"]:
            result.is_valid = False
            result.confidence = 0.0
            result.issues.append("Duration is missing or contains placeholder text")
            result.needs_reextraction = True
            return result
        
        # Parse duration components
        matches = self.duration_pattern.findall(value)
        if not matches:
            result.is_valid = False
            result.confidence = 0.2
            result.issues.append(f"Cannot parse duration format: '{value}'")
            result.suggestions.append("Use format like '6 months', '2 years', '12 weeks'")
            result.needs_reextraction = True
            return result
        
        # Convert to days for range validation
        total_days = 0
        for amount, unit in matches:
            amount = float(amount)
            unit_lower = unit.lower()
            
            if unit_lower in ["day", "days"]:
                total_days += amount
            elif unit_lower in ["week", "weeks"]:
                total_days += amount * 7
            elif unit_lower in ["month", "months"]:
                total_days += amount * 30
            elif unit_lower in ["year", "years"]:
                total_days += amount * 365
            elif unit_lower in ["hour", "hours"]:
                total_days += amount / 24
            elif unit_lower in ["minute", "minutes"]:
                total_days += amount / 1440
            else:
                # Visit/cycle - can't convert to days reliably
                result.confidence = 0.8
                result.suggestions.append(f"Consider adding time estimate for '{unit}'")
        
        # Validate range
        if total_days > 0:
            if total_days < self.duration_ranges["min_days"]:
                result.confidence = 0.6
                result.issues.append(f"Duration seems too short: {total_days:.1f} days")
            elif total_days > self.duration_ranges["max_days"]:
                result.confidence = 0.5
                result.issues.append(f"Duration seems too long: {total_days:.1f} days")
            elif (total_days < self.duration_ranges["typical_min"] or 
                  total_days > self.duration_ranges["typical_max"]):
                result.confidence = max(0.7, result.confidence - 0.1)
                result.suggestions.append(f"Duration of {total_days:.1f} days is outside typical range")
        
        # Check for range expressions
        if "up to" in value.lower() or "approximately" in value.lower():
            result.confidence = min(0.9, result.confidence)  # Slightly lower confidence for estimates
        
        return result
    
    def validate_risks(self, value: str, study_object: str = None) -> FieldValidationResult:
        """
        Validate key risks field - simplified KISS approach
        
        Args:
            value: Risks description
            study_object: Type of study object (for context)
            
        Returns:
            FieldValidationResult
        """
        result = FieldValidationResult(
            field_name="key_risks",
            value=value,
            is_valid=True,
            confidence=1.0
        )
        
        # Check for generic/placeholder risks
        if not value or value.lower() in ["standard medical risks", "minimal risks", "none"]:
            result.is_valid = False
            result.confidence = 0.3
            result.issues.append("Too generic or missing")
            result.needs_reextraction = True
            return result
        
        # Has substance? Good enough (5+ words)
        word_count = len(value.split())
        if word_count > 5:
            result.confidence = 0.9
            return result
        
        # Too brief but not empty
        if word_count >= 3:
            result.confidence = 0.7
            result.suggestions.append("Could be more specific")
            return result
        
        # Very brief
        result.confidence = 0.5
        result.issues.append("Risk description too brief")
        return result
    
    def validate_population(self, 
                           population_type: PopulationType,
                           is_pediatric: bool) -> FieldValidationResult:
        """
        Validate population consistency
        
        Args:
            population_type: Selected population type
            is_pediatric: Whether study includes children
            
        Returns:
            FieldValidationResult
        """
        result = FieldValidationResult(
            field_name="population",
            value=population_type,
            is_valid=True,
            confidence=1.0
        )
        
        # Check pediatric consistency
        if is_pediatric:
            if population_type not in [PopulationType.CHILDREN, 
                                      PopulationType.LARGE_NUMBERS_CHILDREN,
                                      PopulationType.SMALL_NUMBERS_CHILDREN]:
                result.is_valid = False
                result.confidence = 0.2
                result.issues.append("Pediatric flag set but population doesn't mention children")
                result.refined_value = PopulationType.CHILDREN
        else:
            if "children" in population_type.value.lower():
                result.is_valid = False
                result.confidence = 0.3
                result.issues.append("Population mentions children but pediatric flag is False")
        
        return result
    
    def validate_study_purpose(self, value: str, study_type: StudyType) -> FieldValidationResult:
        """
        Validate study purpose description
        
        Args:
            value: Purpose description
            study_type: Type of study (studying vs collecting)
            
        Returns:
            FieldValidationResult
        """
        result = FieldValidationResult(
            field_name="study_purpose",
            value=value,
            is_valid=True,
            confidence=1.0
        )
        
        # Check for empty or too generic
        if not value or len(value) < 10:
            result.is_valid = False
            result.confidence = 0.2
            result.issues.append("Study purpose is missing or too brief")
            result.needs_reextraction = True
            return result
        
        # Check word count (10-15 words ideal)
        word_count = len(value.split())
        if word_count < 5:
            result.confidence = 0.5
            result.issues.append("Purpose too brief - should be 10-15 words")
        elif word_count > 25:
            result.confidence = 0.8
            result.suggestions.append("Consider condensing purpose to 10-15 words")
        
        # Check alignment with study type
        value_lower = value.lower()
        if study_type == StudyType.STUDYING:
            studying_keywords = ["evaluate", "test", "assess", "examine", "investigate", "determine"]
            if not any(keyword in value_lower for keyword in studying_keywords):
                result.confidence = min(0.7, result.confidence)
                result.suggestions.append("Purpose should use action verbs like 'evaluate' or 'test'")
        else:  # COLLECTING
            collecting_keywords = ["collect", "gather", "obtain", "record", "document", "survey"]
            if not any(keyword in value_lower for keyword in collecting_keywords):
                result.confidence = min(0.7, result.confidence)
                result.suggestions.append("Purpose should mention data collection activities")
        
        return result
    
    def _infer_study_type(self, study_object: str) -> str:
        """Infer study type from study object description"""
        obj_lower = study_object.lower()
        
        if any(word in obj_lower for word in ["device", "implant", "equipment"]):
            return "device"
        elif any(word in obj_lower for word in ["drug", "medication", "medicine", "treatment"]):
            return "drug"
        elif any(word in obj_lower for word in ["radiation", "x-ray", "imaging", "scan"]):
            return "radiation"
        elif any(word in obj_lower for word in ["genetic", "dna", "gene"]):
            return "genetic"
        elif any(word in obj_lower for word in ["behavioral", "survey", "questionnaire"]):
            return "behavioral"
        
        return "general"


class CrossFieldValidator:
    """
    Validates consistency across multiple fields
    Ensures logical relationships between extracted values
    """
    
    def __init__(self):
        """Initialize cross-field validator"""
        self.validation_rules = self._build_validation_rules()
    
    def _build_validation_rules(self) -> List[Dict[str, Any]]:
        """Build cross-field validation rules"""
        return [
            {
                "name": "pediatric_consent_consistency",
                "description": "Pediatric studies should mention parental consent",
                "check": lambda e: not e.is_pediatric or 
                        any(word in str(e.benefit_description).lower() 
                            for word in ["parent", "guardian", "assent"]),
                "confidence_impact": 0.3,
                "message": "Pediatric study but no mention of parental consent"
            },
            {
                "name": "randomization_groups",
                "description": "Randomized studies should mention groups/arms",
                "check": lambda e: not e.has_randomization or
                        any(word in str(e.study_purpose).lower() + str(e.study_goals).lower()
                            for word in ["group", "arm", "randomize", "assign"]),
                "confidence_impact": 0.2,
                "message": "Randomized study but no mention of groups/arms"
            },
            {
                "name": "washout_medication",
                "description": "Washout studies should mention medication risks",
                "check": lambda e: not e.requires_washout or
                        any(word in str(e.key_risks).lower()
                            for word in ["medication", "drug", "withdrawal", "washout"]),
                "confidence_impact": 0.25,
                "message": "Washout required but no medication-related risks mentioned"
            },
            {
                "name": "biospecimen_collection",
                "description": "Biospecimen collection should be reflected in risks",
                "check": lambda e: not e.collects_biospecimens or
                        any(word in str(e.key_risks).lower()
                            for word in ["blood", "tissue", "sample", "specimen", "biopsy"]),
                "confidence_impact": 0.2,
                "message": "Collects biospecimens but not mentioned in risks"
            },
            {
                "name": "treatment_alternatives",
                "description": "If treatment affected, alternatives should be specified",
                "check": lambda e: not e.affects_treatment or
                        (e.alternative_options and len(str(e.alternative_options)) > 10),
                "confidence_impact": 0.3,
                "message": "Treatment affected but no alternatives specified"
            }
        ]
    
    def validate(self, extraction: KIExtractionSchema) -> Tuple[List[str], float]:
        """
        Validate cross-field consistency
        
        Args:
            extraction: Extracted KI schema
            
        Returns:
            Tuple of (issues list, confidence adjustment)
        """
        issues = []
        confidence_penalty = 0.0
        
        for rule in self.validation_rules:
            try:
                if not rule["check"](extraction):
                    issues.append(rule["message"])
                    confidence_penalty += rule["confidence_impact"]
                    logger.debug(f"Cross-field validation failed: {rule['name']}")
            except Exception as e:
                logger.error(f"Error in cross-field validation rule {rule['name']}: {e}")
        
        return issues, max(0.1, 1.0 - confidence_penalty)


class SelfHealingExtractor:
    """
    Self-healing extraction system with automatic correction
    Attempts to fix validation issues through targeted re-extraction
    """
    
    def __init__(self, llm_extractor, max_attempts: int = 3):
        """
        Initialize self-healing extractor
        
        Args:
            llm_extractor: LLM extraction instance
            max_attempts: Maximum extraction attempts
        """
        self.llm = llm_extractor
        self.semantic_validator = SemanticFieldValidator()
        self.cross_validator = CrossFieldValidator()
        self.max_attempts = max_attempts
        self.confidence_threshold = CONFIDENCE_THRESHOLD  # Use single config constant
    
    async def extract_with_validation(self,
                                     document_context: str,
                                     output_cls: type[BaseModel]) -> Tuple[BaseModel, DocumentValidationResult]:
        """
        Extract with semantic validation and self-healing
        
        Args:
            document_context: Document text
            output_cls: Pydantic model class for extraction
            
        Returns:
            Tuple of (extracted model, validation result)
        """
        best_extraction = None
        best_validation = None
        best_confidence = 0.0
        
        for attempt in range(self.max_attempts):
            logger.info(f"Extraction attempt {attempt + 1}/{self.max_attempts}")
            
            # Extract using LLM
            try:
                if attempt == 0:
                    # First attempt: standard extraction
                    extraction = await self.llm.extract_structured(
                        document_context=document_context,
                        output_cls=output_cls
                    )
                else:
                    # Subsequent attempts: add guidance based on previous issues
                    guidance = self._create_refinement_guidance(best_validation)
                    extraction = await self.llm.extract_structured(
                        document_context=document_context,
                        output_cls=output_cls,
                        system_prompt=guidance
                    )
            except Exception as e:
                logger.error(f"Extraction failed on attempt {attempt + 1}: {e}")
                continue
            
            # Validate extraction
            validation = await self.validate_extraction(extraction, document_context)
            validation.extraction_attempts = attempt + 1
            
            # Check if we've reached acceptable confidence
            if validation.overall_confidence >= self.confidence_threshold:
                logger.info(f"Achieved confidence {validation.overall_confidence:.2%} on attempt {attempt + 1}")
                return extraction, validation
            
            # Keep best attempt
            if validation.overall_confidence > best_confidence:
                best_extraction = extraction
                best_validation = validation
                best_confidence = validation.overall_confidence
            
            # If confidence is critically low, try targeted field refinement
            if validation.overall_confidence < 0.5 and attempt < self.max_attempts - 1:
                extraction = await self._refine_problematic_fields(
                    extraction, validation, document_context
                )
        
        # Make validation advisory, not blocking - just flag low confidence
        if best_validation and best_validation.overall_confidence < self.confidence_threshold:
            best_validation.requires_human_review = True
            logger.warning(f"Low confidence: {best_confidence:.2%} - flagged for review")
            # But still return the extraction! Don't block.
        
        return best_extraction, best_validation
    
    async def validate_extraction(self, 
                                 extraction: KIExtractionSchema,
                                 document_context: str) -> DocumentValidationResult:
        """
        Perform comprehensive validation on extraction
        
        Args:
            extraction: Extracted schema
            document_context: Original document for reference
            
        Returns:
            DocumentValidationResult with field-level and cross-field validation
        """
        field_results = {}
        total_confidence = 0.0
        field_count = 0
        
        # Validate individual fields
        if isinstance(extraction, KIExtractionSchema):
            # Duration validation
            field_results["study_duration"] = self.semantic_validator.validate_duration(
                extraction.study_duration
            )
            
            # Risk validation
            field_results["key_risks"] = self.semantic_validator.validate_risks(
                extraction.key_risks,
                extraction.study_object
            )
            
            # Population validation
            field_results["population"] = self.semantic_validator.validate_population(
                extraction.population,
                extraction.is_pediatric
            )
            
            # Purpose validation
            field_results["study_purpose"] = self.semantic_validator.validate_study_purpose(
                extraction.study_purpose,
                extraction.study_type
            )
            
            # Calculate average confidence
            for result in field_results.values():
                total_confidence += result.confidence
                field_count += 1
        
        # Cross-field validation
        cross_issues, cross_confidence = self.cross_validator.validate(extraction)
        
        # Calculate overall confidence
        field_confidence = total_confidence / max(1, field_count)
        overall_confidence = (field_confidence * 0.7 + cross_confidence * 0.3)
        
        # Determine overall validity
        is_valid = all(r.is_valid for r in field_results.values()) and len(cross_issues) == 0
        
        return DocumentValidationResult(
            is_valid=is_valid,
            overall_confidence=overall_confidence,
            field_results=field_results,
            cross_field_issues=cross_issues,
            requires_human_review=(overall_confidence < 0.7)
        )
    
    def _create_refinement_guidance(self, validation: DocumentValidationResult) -> str:
        """
        Create targeted guidance for re-extraction based on validation issues
        
        Args:
            validation: Previous validation result
            
        Returns:
            System prompt with specific guidance
        """
        guidance_parts = [
            "You are an expert at extracting information from IRB consent documents.",
            "Previous extraction had issues. Please pay special attention to:"
        ]
        
        # Add field-specific guidance
        for field_name, result in validation.field_results.items():
            if result.confidence < 0.8:
                guidance_parts.append(f"\n{field_name}:")
                for issue in result.issues:
                    guidance_parts.append(f"  - {issue}")
                for suggestion in result.suggestions:
                    guidance_parts.append(f"  - Suggestion: {suggestion}")
        
        # Add cross-field guidance
        if validation.cross_field_issues:
            guidance_parts.append("\nCross-field consistency:")
            for issue in validation.cross_field_issues:
                guidance_parts.append(f"  - {issue}")
        
        guidance_parts.append("\nPlease extract all fields accurately, addressing the issues above.")
        
        return "\n".join(guidance_parts)
    
    async def _refine_problematic_fields(self,
                                        extraction: BaseModel,
                                        validation: DocumentValidationResult,
                                        document_context: str) -> BaseModel:
        """
        Attempt to refine specific problematic fields
        
        Args:
            extraction: Current extraction
            validation: Validation results
            document_context: Document text
            
        Returns:
            Refined extraction
        """
        problematic_fields = validation.get_problematic_fields()
        
        for field_name in problematic_fields:
            if field_name in validation.field_results:
                field_result = validation.field_results[field_name]
                
                if field_result.needs_reextraction:
                    # Create targeted prompt for this field
                    field_prompt = self._create_field_refinement_prompt(
                        field_name, field_result, document_context
                    )
                    
                    try:
                        # Re-extract just this field
                        refined_value = await self.llm.extract_text(
                            document_context=document_context,
                            query=field_prompt,
                            max_words=50
                        )
                        
                        # Update extraction
                        if hasattr(extraction, field_name):
                            setattr(extraction, field_name, refined_value)
                            logger.info(f"Refined field {field_name}: {refined_value}")
                    except Exception as e:
                        logger.error(f"Failed to refine field {field_name}: {e}")
        
        return extraction
    
    def _create_field_refinement_prompt(self,
                                       field_name: str,
                                       field_result: FieldValidationResult,
                                       document_context: str) -> str:
        """
        Create specific prompt for refining a single field
        
        Args:
            field_name: Name of field to refine
            field_result: Validation result for the field
            document_context: Document text (for context)
            
        Returns:
            Refinement prompt
        """
        prompts = {
            "study_duration": (
                "Extract the EXACT study duration from the document. "
                "Look for phrases like 'study will last', 'participation duration', 'total time'. "
                "Return in format like '6 months', '2 years', '12 weeks'. "
                "If not found, return empty string. Do NOT use placeholders."
            ),
            "key_risks": (
                "Extract the 2-3 most important study-specific risks. "
                "Focus on risks from the study procedures, not standard medical care. "
                "Include specific mentions of pain, discomfort, or side effects. "
                "Be specific and concise (30 words max)."
            ),
            "study_purpose": (
                "Extract the main study purpose in 10-15 words. "
                "Use action verbs like 'evaluate', 'test', 'assess'. "
                "Be specific about what is being studied. "
                "Avoid generic phrases."
            )
        }
        
        base_prompt = prompts.get(field_name, f"Extract the {field_name} from the document.")
        
        # Add specific issues to address
        if field_result.issues:
            base_prompt += f"\n\nAddress these issues: {', '.join(field_result.issues)}"
        
        return base_prompt


# Integration helper for existing pipeline
async def validate_and_heal_extraction(
    extraction: Union[KIExtractionSchema, ClinicalProtocolExtractionSchema],
    document_context: str,
    llm_extractor=None
) -> Tuple[Any, DocumentValidationResult]:
    """
    Convenience function to validate and heal an extraction
    
    Args:
        extraction: Initial extraction
        document_context: Document text
        llm_extractor: Optional LLM extractor (will create if not provided)
        
    Returns:
        Tuple of (healed extraction, validation result)
    """
    # Get LLM extractor
    if llm_extractor is None:
        from app.core.llm_integration import get_generic_extractor
        llm_extractor = get_generic_extractor()
    
    # Create self-healing extractor
    healer = SelfHealingExtractor(llm_extractor)
    
    # If we already have an extraction, validate it
    if extraction:
        validation = await healer.validate_extraction(extraction, document_context)
        
        # If validation is good enough, return as-is
        if validation.overall_confidence >= healer.confidence_threshold:
            return extraction, validation
        
        # Otherwise, try to heal
        refined = await healer._refine_problematic_fields(
            extraction, validation, document_context
        )
        
        # Re-validate
        final_validation = await healer.validate_extraction(refined, document_context)
        return refined, final_validation
    
    # No extraction provided, do full extraction with validation
    return await healer.extract_with_validation(
        document_context,
        type(extraction) if extraction else KIExtractionSchema
    )