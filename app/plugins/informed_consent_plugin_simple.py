"""
Simplified Informed Consent Key Information Summary Plugin
Streamlined implementation using UnifiedExtractor
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.core.plugin_base import SimpleDocumentPlugin, PluginConfig
from app.core.unified_extractor import UnifiedExtractor
from app.core.extraction_models import KIExtractionSchema
from app.logger import get_logger

logger = get_logger("plugins.informed_consent")

# KI extraction schema (simplified from 483 lines to essential fields)
KI_SCHEMA = {
    "is_pediatric": {
        "type": "boolean",
        "description": "Are children eligible to participate?"
    },
    "study_type": {
        "type": "enum",
        "options": ["studying", "collecting"],
        "description": "Is this study primarily studying/testing or collecting/gathering?"
    },
    "article": {
        "type": "enum",
        "options": ["a ", "a new ", ""],
        "description": "Article before study object"
    },
    "study_object": {
        "type": "text",
        "max_words": 30,
        "description": "Main object being studied (drug, device, procedure)"
    },
    "population": {
        "type": "enum",
        "options": ["people", "large numbers of people", "small numbers of people", 
                   "children", "large numbers of children", "small numbers of children"],
        "description": "Population that will participate"
    },
    "study_purpose": {
        "type": "text",
        "max_words": 15,
        "description": "Main purpose of study"
    },
    "study_goals": {
        "type": "text",
        "max_words": 15,
        "description": "What study will accomplish"
    },
    "has_randomization": {
        "type": "boolean",
        "description": "Does study use randomization?"
    },
    "key_risks": {
        "type": "text",
        "max_words": 30,
        "description": "2-3 most important risks"
    },
    "has_direct_benefits": {
        "type": "boolean",
        "description": "Are there direct benefits to participants?"
    },
    "benefit_description": {
        "type": "text",
        "max_words": 20,
        "description": "Benefits summary"
    },
    "study_duration": {
        "type": "text",
        "max_words": 10,
        "description": "How long participants will be in study"
    },
    "affects_treatment": {
        "type": "boolean",
        "description": "Does participation affect treatment options?"
    },
    "alternative_options": {
        "type": "text",
        "max_words": 20,
        "description": "Treatment alternatives if applicable"
    },
    "collects_biospecimens": {
        "type": "boolean",
        "description": "Will biological specimens be collected?"
    },
    "biospecimen_details": {
        "type": "text",
        "max_words": 30,
        "description": "Details about specimen collection"
    }
}


class InformedConsentPlugin(SimpleDocumentPlugin):
    """
    Simplified Informed Consent plugin using UnifiedExtractor.
    Reduced from 483 lines to ~150 lines.
    """
    
    def get_config(self) -> PluginConfig:
        """Return plugin configuration"""
        return PluginConfig(
            name="Informed Consent Key Information Summary",
            version="6.0.0",
            supported_types=["informed-consent", "consent-form", "irb-consent", "informed-consent-ki"],
            template_dir="informed-consent",
            extraction_schema=KI_SCHEMA,
            critical_fields=["study_object", "key_risks", "study_duration", "study_purpose"]
        )
    
    async def extract(self, document: str, llm_client: Any = None) -> Dict[str, Any]:
        """
        Extract structured data using UnifiedExtractor with KI schema.
        
        Args:
            document: Document text to extract from
            llm_client: Optional LLM client for extraction
            
        Returns:
            Dictionary of extracted values
        """
        try:
            logger.info("Chain-of-thought extraction initialized")
            
            # Use UnifiedExtractor with structured extraction
            extractor = UnifiedExtractor(llm_client)
            result = await extractor.extract(
                document=document,
                output_schema=KIExtractionSchema
            )
            
            # Convert Pydantic model to dict
            extracted = result.model_dump()
            
            # Process extracted values for template use
            processed = self._process_extracted_values(extracted)
            
            logger.info(f"Extraction completed successfully")
            return processed
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            # Return sensible defaults
            return self._get_default_values()
    
    def get_template_path(self, template_name: str = "main") -> str:
        """
        Get path to template file.
        
        Args:
            template_name: Name of template (default: "main")
            
        Returns:
            Path to template file
        """
        if template_name == "main":
            return f"{self.config.template_dir}/ki-summary.j2"
        else:
            return f"{self.config.template_dir}/sections/{template_name}.j2"
    
    def _process_extracted_values(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Process extracted values for template consumption"""
        processed = extracted.copy()
        
        # Generate benefit statement
        if extracted.get("has_direct_benefits"):
            benefit_detail = extracted.get("benefit_description", "helping advance medical knowledge")
            processed["benefit_statement"] = f"You may benefit by {benefit_detail}."
        else:
            processed["benefit_statement"] = "You may not benefit directly, but may help others in the future."
        
        # Generate randomization text
        if extracted.get("has_randomization"):
            study_obj = extracted.get("study_object", "").lower()
            if "device" in study_obj:
                processed["randomization_text"] = "You will be randomly assigned (like flipping a coin) to use either the study device or standard device."
            elif "procedure" in study_obj:
                processed["randomization_text"] = "You will be randomly assigned (like flipping a coin) to receive the study procedure or standard procedure."
            else:
                processed["randomization_text"] = "You will be randomly assigned (like flipping a coin) to one of the study groups."
        else:
            processed["randomization_text"] = ""
        
        # Generate alternatives sentence
        if extracted.get("affects_treatment") and extracted.get("alternative_options"):
            processed["alternatives_sentence"] = f"Other choices include: {extracted['alternative_options']}."
        else:
            processed["alternatives_sentence"] = ""
        
        # Generate biospecimen statement
        if extracted.get("collects_biospecimens"):
            processed["biospecimen_statement"] = extracted.get("biospecimen_details", "Biological samples will be collected.")
        else:
            processed["biospecimen_statement"] = ""
        
        return processed
    
    def _get_default_values(self) -> Dict[str, Any]:
        """Return default values when extraction fails"""
        return {
            "is_pediatric": False,
            "study_type": "studying",
            "article": "a ",
            "study_object": "intervention",
            "population": "people",
            "study_purpose": "evaluate effectiveness",
            "study_goals": "gather data",
            "has_randomization": False,
            "key_risks": "standard medical risks",
            "has_direct_benefits": False,
            "benefit_description": "helping advance medical knowledge",
            "benefit_statement": "You may not benefit directly, but may help others in the future.",
            "study_duration": "varies",
            "affects_treatment": False,
            "alternative_options": "",
            "alternatives_sentence": "",
            "collects_biospecimens": False,
            "biospecimen_details": "",
            "biospecimen_statement": "",
            "randomization_text": ""
        }