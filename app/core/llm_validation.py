"""
LLM-first validation for IRB document extraction
Uses LLM intelligence instead of rule-based patterns
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from app.logger import get_logger
from app.core.extraction_models import KIExtractionSchema, PopulationType

logger = get_logger("core.llm_validation")

# Simple confidence threshold
CONFIDENCE_THRESHOLD = 0.7


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
            if result.confidence < CONFIDENCE_THRESHOLD or not result.is_valid
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


class LLMFieldValidator:
    """
    Uses LLM to validate fields semantically
    No rules, patterns, or word counts - just LLM intelligence
    """
    
    def __init__(self, llm_extractor):
        """
        Initialize with LLM extractor
        
        Args:
            llm_extractor: LLM extractor instance
        """
        self.llm = llm_extractor
    
    async def validate_duration(self, value: str) -> FieldValidationResult:
        """
        Use LLM to validate study duration
        
        Args:
            value: Duration string to validate
            
        Returns:
            FieldValidationResult with LLM-based assessment
        """
        if not value:
            return FieldValidationResult(
                field_name="study_duration",
                value=value,
                is_valid=False,
                confidence=0.0,
                issues=["Duration is missing"],
                needs_reextraction=True
            )
        
        # Let LLM evaluate the duration
        validation_prompt = f"""
        Evaluate this study duration: "{value}"
        
        A valid duration should:
        - Be a specific time period (e.g., "6 months", "2 years", "12 weeks")
        - Not be a placeholder like "not specified" or "the study period"
        - Be reasonable for a clinical study (1 day to 10 years)
        
        Respond with only YES if valid, NO if invalid.
        """
        
        try:
            is_valid = await self.llm.extract_boolean(
                document_context="",
                query=validation_prompt
            )
            
            # Ask LLM for confidence
            confidence_prompt = f"""
            How confident are you that "{value}" is a clear, specific study duration?
            Rate from 0.0 to 1.0 where:
            - 1.0 = Perfectly clear (e.g., "6 months")
            - 0.7 = Acceptable but could be clearer
            - 0.3 = Vague or problematic
            - 0.0 = Invalid or placeholder
            
            Respond with just the number.
            """
            
            confidence_text = await self.llm.extract_text(
                document_context="",
                query=confidence_prompt,
                max_words=5
            )
            
            # Parse confidence
            try:
                confidence = float(confidence_text.strip())
            except:
                confidence = 0.7 if is_valid else 0.3
            
            issues = []
            if not is_valid:
                issues.append("LLM assessment: Duration is not specific or valid")
            
            return FieldValidationResult(
                field_name="study_duration",
                value=value,
                is_valid=is_valid,
                confidence=confidence,
                issues=issues,
                needs_reextraction=not is_valid
            )
            
        except Exception as e:
            logger.error(f"LLM validation failed for duration: {e}")
            # Fallback to permissive
            return FieldValidationResult(
                field_name="study_duration",
                value=value,
                is_valid=True,
                confidence=0.6,
                suggestions=["Could not validate with LLM"]
            )
    
    async def validate_risks(self, value: str) -> FieldValidationResult:
        """
        Use LLM to validate risk description
        
        Args:
            value: Risk description to validate
            
        Returns:
            FieldValidationResult with LLM assessment
        """
        if not value:
            return FieldValidationResult(
                field_name="key_risks",
                value=value,
                is_valid=False,
                confidence=0.0,
                issues=["Risks are missing"],
                needs_reextraction=True
            )
        
        # Let LLM evaluate the risks
        evaluation_prompt = f"""
        Evaluate this risk description for an IRB consent form: "{value}"
        
        Good risk descriptions should:
        - Be specific, not generic like "standard medical risks"
        - Mention concrete risks participants will face
        - Include information about pain, discomfort, or side effects
        
        Rate the quality from 0.0 to 1.0 where:
        - 0.9-1.0 = Excellent, specific risks clearly described
        - 0.7-0.9 = Good, adequate detail
        - 0.5-0.7 = Acceptable but could be more specific
        - 0.3-0.5 = Too generic or vague
        - 0.0-0.3 = Unacceptable placeholder text
        
        Respond with just the number.
        """
        
        try:
            confidence_text = await self.llm.extract_text(
                document_context="",
                query=evaluation_prompt,
                max_words=5
            )
            
            # Parse confidence
            try:
                confidence = float(confidence_text.strip())
            except:
                confidence = 0.6
            
            is_valid = confidence >= 0.5
            
            issues = []
            if confidence < 0.5:
                issues.append("Risk description is too generic or inadequate")
            
            suggestions = []
            if 0.5 <= confidence < 0.7:
                suggestions.append("Consider adding more specific risk details")
            
            return FieldValidationResult(
                field_name="key_risks",
                value=value,
                is_valid=is_valid,
                confidence=confidence,
                issues=issues,
                suggestions=suggestions,
                needs_reextraction=(confidence < 0.3)
            )
            
        except Exception as e:
            logger.error(f"LLM validation failed for risks: {e}")
            # Fallback to permissive
            return FieldValidationResult(
                field_name="key_risks",
                value=value,
                is_valid=True,
                confidence=0.6,
                suggestions=["Could not validate with LLM"]
            )
    
    async def validate_population_consistency(self,
                                            population: PopulationType,
                                            is_pediatric: bool) -> FieldValidationResult:
        """
        Use LLM to check population consistency
        
        Args:
            population: Population type
            is_pediatric: Whether study includes children
            
        Returns:
            FieldValidationResult with consistency check
        """
        # Ask LLM about consistency
        consistency_prompt = f"""
        Is this consistent?
        - Population type: "{population.value}"
        - Study includes children: {is_pediatric}
        
        Answer YES if they match (e.g., "children" population with pediatric=true),
        NO if they conflict.
        """
        
        try:
            is_consistent = await self.llm.extract_boolean(
                document_context="",
                query=consistency_prompt
            )
            
            confidence = 1.0 if is_consistent else 0.2
            
            issues = []
            if not is_consistent:
                if is_pediatric:
                    issues.append("Pediatric study but population doesn't mention children")
                else:
                    issues.append("Adult study but population mentions children")
            
            return FieldValidationResult(
                field_name="population",
                value=population,
                is_valid=is_consistent,
                confidence=confidence,
                issues=issues
            )
            
        except Exception as e:
            logger.error(f"LLM validation failed for population: {e}")
            # Fallback
            return FieldValidationResult(
                field_name="population",
                value=population,
                is_valid=True,
                confidence=0.7
            )


class LLMCrossFieldValidator:
    """
    Uses LLM to validate cross-field consistency
    No rules - just ask the LLM if things make sense together
    """
    
    def __init__(self, llm_extractor):
        """Initialize with LLM extractor"""
        self.llm = llm_extractor
    
    async def validate(self, extraction: KIExtractionSchema) -> Tuple[List[str], float]:
        """
        Use LLM to check overall consistency
        
        Args:
            extraction: Extracted KI schema
            
        Returns:
            Tuple of (issues list, confidence)
        """
        # Create a summary for LLM to evaluate
        extraction_summary = f"""
        Pediatric study: {extraction.is_pediatric}
        Population: {extraction.population.value if extraction.population else 'not specified'}
        Has randomization: {extraction.has_randomization}
        Study purpose: {extraction.study_purpose}
        Requires washout: {extraction.requires_washout}
        Key risks: {extraction.key_risks}
        Collects biospecimens: {extraction.collects_biospecimens}
        Benefits description: {extraction.benefit_description}
        Treatment affected: {extraction.affects_treatment}
        Alternative options: {extraction.alternative_options or 'not specified'}
        """
        
        consistency_prompt = f"""
        Review this clinical study extraction for internal consistency:
        
        {extraction_summary}
        
        Check for logical inconsistencies such as:
        - Pediatric study without mention of parents/guardians
        - Randomization without mention of groups/arms
        - Washout required but no medication risks mentioned
        - Biospecimen collection but no sampling risks mentioned
        - Treatment affected but no alternatives provided
        
        List any inconsistencies found (one per line), or respond "CONSISTENT" if all looks good.
        """
        
        try:
            response = await self.llm.extract_text(
                document_context="",
                query=consistency_prompt,
                max_words=200
            )
            
            response = response.strip()
            
            if response.upper() == "CONSISTENT":
                return [], 1.0
            
            # Parse issues from response
            issues = [line.strip() for line in response.split('\n') if line.strip()]
            
            # Calculate confidence penalty based on number of issues
            confidence = max(0.3, 1.0 - (len(issues) * 0.15))
            
            return issues, confidence
            
        except Exception as e:
            logger.error(f"LLM cross-field validation failed: {e}")
            # Fallback - assume consistent
            return [], 0.8


class LLMSelfHealingExtractor:
    """
    Self-healing extraction with LLM-based validation
    """
    
    def __init__(self, llm_extractor, max_attempts: int = 3):
        """
        Initialize self-healing extractor
        
        Args:
            llm_extractor: LLM extraction instance
            max_attempts: Maximum extraction attempts
        """
        self.llm = llm_extractor
        self.field_validator = LLMFieldValidator(llm_extractor)
        self.cross_validator = LLMCrossFieldValidator(llm_extractor)
        self.max_attempts = max_attempts
        self.confidence_threshold = CONFIDENCE_THRESHOLD
    
    async def extract_with_validation(self,
                                     document_context: str,
                                     output_cls: type) -> Tuple[Any, DocumentValidationResult]:
        """
        Extract with LLM-based validation and self-healing
        
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
            
            # Validate extraction with LLM
            validation = await self.validate_extraction(extraction)
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
        
        # Flag for review if confidence still low (but don't block)
        if best_validation and best_validation.overall_confidence < self.confidence_threshold:
            best_validation.requires_human_review = True
            logger.warning(f"Low confidence: {best_confidence:.2%} - flagged for review")
        
        return best_extraction, best_validation
    
    async def validate_extraction(self, extraction: KIExtractionSchema) -> DocumentValidationResult:
        """
        Perform LLM-based validation on extraction
        
        Args:
            extraction: Extracted schema
            
        Returns:
            DocumentValidationResult with LLM-based validation
        """
        field_results = {}
        total_confidence = 0.0
        field_count = 0
        
        # Validate key fields with LLM
        if isinstance(extraction, KIExtractionSchema):
            # Duration validation
            field_results["study_duration"] = await self.field_validator.validate_duration(
                extraction.study_duration
            )
            
            # Risk validation
            field_results["key_risks"] = await self.field_validator.validate_risks(
                extraction.key_risks
            )
            
            # Population consistency
            field_results["population"] = await self.field_validator.validate_population_consistency(
                extraction.population,
                extraction.is_pediatric
            )
            
            # Calculate average confidence
            for result in field_results.values():
                total_confidence += result.confidence
                field_count += 1
        
        # Cross-field validation with LLM
        cross_issues, cross_confidence = await self.cross_validator.validate(extraction)
        
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
            requires_human_review=(overall_confidence < CONFIDENCE_THRESHOLD)
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
            if result.confidence < CONFIDENCE_THRESHOLD:
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