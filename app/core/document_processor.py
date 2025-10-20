"""
Simplified Document Processing Pipeline
Replaces complex multi-agent system with clean functions
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from app.core.unified_extractor import UnifiedExtractor
from app.core.validators import ValidationOrchestrator
from app.core.exceptions import ExtractionError
from app.logger import get_logger

logger = get_logger("core.document_processor")


@dataclass
class ProcessingContext:
    """Simple context for document processing"""
    document_text: str
    document_type: str
    extracted_values: Dict[str, Any] = None
    generated_content: Dict[str, Any] = None
    validation_results: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extracted_values is None:
            self.extracted_values = {}
        if self.generated_content is None:
            self.generated_content = {}
        if self.validation_results is None:
            self.validation_results = {}


class SimpleDocumentProcessor:
    """
    Simplified document processor replacing multi-agent system.
    Reduces from 512 lines to ~150 lines.
    """
    
    def __init__(self, llm_client=None):
        """
        Initialize processor with optional LLM client.
        
        Args:
            llm_client: Optional LLM client for extraction and generation
        """
        self.extractor = UnifiedExtractor(llm_client)
        self.validator = ValidationOrchestrator()
        self.llm_client = llm_client
    
    async def process(self, 
                     document_text: str,
                     document_type: str,
                     output_schema: Any,
                     critical_fields: List[str] = None) -> ProcessingContext:
        """
        Process document through extraction, generation, and validation pipeline.
        
        Args:
            document_text: Document to process
            document_type: Type of document
            output_schema: Pydantic schema for extraction
            critical_fields: Fields that must be preserved
            
        Returns:
            ProcessingContext with all results
        """
        # Create context
        context = ProcessingContext(
            document_text=document_text,
            document_type=document_type
        )
        
        # Step 1: Extract structured data
        try:
            extracted = await self.extractor.extract(
                document=document_text,
                output_schema=output_schema
            )

            # Convert to dict if needed
            if hasattr(extracted, 'model_dump'):
                context.extracted_values = extracted.model_dump(mode='json')
            elif hasattr(extracted, 'dict'):
                context.extracted_values = extracted.dict()
            else:
                context.extracted_values = extracted

            # Validate extraction results
            if not context.extracted_values:
                logger.error("Extraction returned empty results")
                raise ExtractionError(
                    "No data could be extracted from document",
                    {"document_length": len(document_text), "document_type": document_type}
                )

            logger.info(f"Extracted {len(context.extracted_values)} fields")

        except ExtractionError:
            # Re-raise extraction errors
            raise
        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            raise ExtractionError(
                str(e),
                {"document_type": document_type, "error_type": type(e).__name__}
            ) from e
        
        # Step 2: Generate content if LLM available
        if self.llm_client and context.extracted_values:
            context.generated_content = await self._generate_content(context)
        
        # Step 3: Validate results
        if critical_fields:
            context.validation_results = self._validate(
                context,
                critical_fields
            )
        
        return context
    
    async def _generate_content(self, context: ProcessingContext) -> Dict[str, Any]:
        """
        Generate content based on extracted values.
        
        Args:
            context: Processing context with extracted values
            
        Returns:
            Generated content dictionary
        """
        generated = {}
        extracted = context.extracted_values
        
        # Generate introduction if title available
        if "study_title" in extracted:
            prompt = f"""Generate a brief, clear introduction for a research study.
            Study Title: {extracted['study_title']}
            Keep it under 100 words and focus on the purpose."""
            
            try:
                response = await self.llm_client.complete(prompt)
                generated["introduction"] = response
            except Exception as e:
                logger.error(f"Generation failed: {e}")
                generated["introduction"] = f"This research study: {extracted['study_title']}"
        
        # Generate summary if key fields available
        if "study_purpose" in extracted and "study_duration" in extracted:
            key_info = {
                "purpose": extracted.get("study_purpose"),
                "duration": extracted.get("study_duration"),
                "risks": extracted.get("key_risks", "standard medical risks")
            }
            
            generated["summary"] = self._format_summary(key_info)
        
        logger.info(f"Generated {len(generated)} content sections")
        return generated
    
    def _format_summary(self, info: Dict[str, Any]) -> str:
        """Format summary from key information"""
        parts = []
        if info.get("purpose"):
            parts.append(f"Purpose: {info['purpose']}")
        if info.get("duration"):
            parts.append(f"Duration: {info['duration']}")
        if info.get("risks"):
            parts.append(f"Main risks: {info['risks']}")
        return " ".join(parts)
    
    def _validate(self, 
                 context: ProcessingContext,
                 critical_fields: List[str]) -> Dict[str, Any]:
        """
        Validate processing results.
        
        Args:
            context: Processing context
            critical_fields: Fields that must be preserved
            
        Returns:
            Validation results
        """
        from app.core.plugin_manager import ValidationRuleSet
        
        # Create validation rules
        rules = ValidationRuleSet(
            required_fields=critical_fields,
            max_lengths={},
            allowed_values={},
            custom_validators=[],
            intent_critical_fields=critical_fields
        )
        
        # Combine extracted and generated for validation
        all_content = {**context.extracted_values, **context.generated_content}
        rendered = str(all_content)
        
        # Run validation
        results = self.validator.validate(
            original=context.extracted_values,
            rendered=rendered,
            rules=rules,
            critical_values=critical_fields,
            document_type=context.document_type
        )
        
        logger.info(f"Validation {'passed' if results['passed'] else 'failed'}")
        return results