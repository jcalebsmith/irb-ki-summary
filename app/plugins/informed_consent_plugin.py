"""
Informed Consent Key Information Summary Plugin
Contains KI-specific extraction logic and templates
"""
import re
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from typing import Dict, Any, List, Optional
from app.core.plugin_manager import DocumentPlugin, TemplateCatalog, ValidationRuleSet, TemplateSlot, SlotType
from app.core.unified_extractor import UnifiedExtractor
from app.core.agent_interfaces import BaseAgent, AgentRole, AgentContext
from app.core.exceptions import ExtractionError
from app.core.extraction_models import KIExtractionSchema, ExtractionReasoning, ReasoningStep
from app.config import TEXT_PROCESSING
from app.logger import get_logger

# Set up module logger
logger = get_logger("plugins.informed_consent")

_TRAILING_CHARS = " .;:,!?\"'"


def _normalize_clause(value: Optional[str], *, lower_leading: bool = False) -> str:
    """Collapse whitespace, trim trailing punctuation, and optionally downcase the leading word."""
    if not value:
        return ""
    cleaned = re.sub(r"\s+", " ", value.strip())
    while cleaned and cleaned[-1] in _TRAILING_CHARS:
        cleaned = cleaned[:-1]

    if lower_leading and cleaned:
        letter_match = re.search(r"[A-Za-z]", cleaned)
        if letter_match:
            idx = letter_match.start()
            word_match = re.match(r"[A-Za-z][A-Za-z0-9'/-]*", cleaned[idx:])
            if word_match:
                word = word_match.group(0)
                if not word.isupper():
                    cleaned = (
                        cleaned[:idx] + word[0].lower() + cleaned[idx + 1 :]
                    )

    return cleaned


# KI-specific extraction schema
KI_EXTRACTION_SCHEMA = {
    "is_pediatric": {
        "type": "boolean",
        "description": "Are children eligible to participate? Look for age requirements, pediatric participants, or parent/guardian consent."
    },
    "study_type": {
        "type": "enum",
        "options": ["studying", "collecting"],
        "description": "Is this study primarily studying/testing something or collecting/gathering something?"
    },
    "article": {
        "type": "enum",
        "options": ["a ", "a new ", ""],
        "description": "What article should precede the study object? 'a ' for existing, 'a new ' for novel, '' for plural/uncountable"
    },
    "study_object": {
        "type": "text",
        "max_words": 30,
        "description": "Main object being studied (e.g., drug, device, procedure). Include FDA status if mentioned. Lowercase."
    },
    "population": {
        "type": "enum",
        "options": ["people", "large numbers of people", "small numbers of people", 
                   "children", "large numbers of children", "small numbers of children"],
        "description": "What population will participate?"
    },
    "study_purpose": {
        "type": "text",
        "max_words": 15,
        "description": "Main purpose of study in 10-15 words. Simple language, no intro phrases."
    },
    "study_goals": {
        "type": "text",
        "max_words": 15,
        "description": "What study will accomplish in 10-15 words. Simple language, direct statement."
    },
    "has_randomization": {
        "type": "boolean",
        "description": "Does document contain words 'randomize', 'randomization', or 'randomized'?"
    },
    "requires_washout": {
        "type": "boolean",
        "description": "Does study require stopping medications before/during participation?"
    },
    "key_risks": {
        "type": "text",
        "max_words": 30,
        "description": "2-3 most important risks from study (not standard care). Focus on pain/distress. 30 words max."
    },
    "has_direct_benefits": {
        "type": "boolean",
        "description": "Are there meaningful direct personal benefits to participants?"
    },
    "benefit_description": {
        "type": "text",
        "max_words": 20,
        "description": "Benefits summary to complete 'by [text]'. Don't include 'by'. 20 words max."
    },
    "study_duration": {
        "type": "text",
        "max_words": 10,
        "description": "How long participants will be in study (e.g., '6 months', 'up to 2 years'). 10 words max."
    },
    "affects_treatment": {
        "type": "boolean",
        "description": "Does participation affect current/future treatment options?"
    },
    "alternative_options": {
        "type": "text",
        "max_words": 20,
        "description": "Treatment alternatives if study affects options. 20 words max."
    },
    "collects_biospecimens": {
        "type": "boolean",
        "description": "Will biological specimens (blood, tissue, DNA, etc.) be collected?"
    },
    "biospecimen_details": {
        "type": "text",
        "max_words": 20,
        "description": "Brief statement about what specimens will be collected. 20 words max."
    }
}

# Conditional template texts
CONDITIONAL_TEMPLATES = {
    "eligibility_children": (
        "You, or your child, may be eligible to take part in a research study. "
        "Parents or legal guardians who are giving permission for a child's "
        "participation in the research, note that in the sections that follow "
        "the word 'you' refers to 'your child'. This form contains information "
        "that will help you decide whether to join the study. All of the "
        "information in this form is important. Take time to carefully review "
        "this information. After you finish, you should talk to the researchers "
        "about the study and ask them any questions you have. You may also wish "
        "to talk to others such as your friends, family, or other doctors about "
        "your possible participation in this study. If you decide to take part "
        "in the study, you will be asked to sign this form. Before you do, be "
        "sure you understand what the study is about."
    ),
    "eligibility_adults": (
        "You may be eligible to take part in a research study. This form contains "
        "important information that will help you decide whether to join the study. "
        "Take the time to carefully review this information. You should talk to the "
        "researchers about the study and ask them any questions you have. You may "
        "also wish to talk to others such as your family, friends, or other doctors "
        "about joining this study. If you decide to join the study, you will be asked "
        "to sign this form before you can start study-related activities. Before you "
        "do, be sure you understand what the research study is about."
    ),
    "randomization": (
        "This study involves a process called randomization. This means that the "
        "drug you receive in the study is not chosen by you or the researcher. "
        "The study design divides study participants into separate groups, based on "
        "chance (like the flip of a coin), to compare different treatments or procedures. "
        "If you decide to be in the study, you need to be comfortable not knowing "
        "which study group you will be in."
    ),
    "randomization_device": (
        "This study involves a process called randomization. This means that the "
        "device you receive in the study is not chosen by you or the researcher. "
        "The study design divides study participants into separate groups, based on "
        "chance (like the flip of a coin), to compare different treatments or procedures. "
        "If you decide to be in the study, you need to be comfortable not knowing "
        "which study group you will be in."
    ),
    "randomization_procedure": (
        "This study involves a process called randomization. This means that the "
        "procedure you receive in the study is not chosen by you or the researcher. "
        "The study design divides study participants into separate groups, based on "
        "chance (like the flip of a coin), to compare different treatments or procedures. "
        "If you decide to be in the study, you need to be comfortable not knowing "
        "which study group you will be in."
    ),
    "washout": (
        "This study may require you to stop taking certain medications before and "
        "possibly during the research study. If you decide to be in the study, you "
        "should understand that some symptoms that were controlled by that medication "
        "may worsen."
    ),
    "benefits_personal": (
        "This study may offer some benefit to you now or others in the future by {benefit_detail}"
    ),
    "benefits_others": (
        "This study may not offer any benefit to you now but may benefit others "
        "in the future by {benefit_detail}"
    ),
    "alternatives": (
        "You can decide not to be in this study. Alternatives to joining this "
        "study include {alternative_options}.\n\n"
    )
}


class KIExtractionAgent(BaseAgent):
    """Agent that performs KI-specific extraction"""
    
    def __init__(self):
        super().__init__("KIExtractionAgent", AgentRole.EXTRACTOR)
        
        # Initialize chain-of-thought extractor
        try:
            self.extractor = UnifiedExtractor()
            logger.info("Unified extractor initialized")
        except Exception as e:
            logger.error(f"Failed to initialize chain-of-thought extraction: {e}")
            raise
        
    async def process(self, agent_context: AgentContext) -> Dict[str, Any]:
        """
        Process document with KI-specific extraction using chain-of-thought
        """
        # Store context for base class
        self.context = agent_context
        
        # Get document context from parameters
        parameters = agent_context.parameters
        
        # Extract document text using utility
        from app.core.utils import DocumentUtils
        document_context = DocumentUtils.extract_document_context(parameters)
        
        try:
            # Use simplified chain-of-thought extraction
            logger.info("Using chain-of-thought extraction for KI document")
            
            # Extract all fields in a single call
            extracted = await self.extractor.extract(
                document=document_context,
                output_schema=KIExtractionSchema
            )
            
            # Store extraction metadata
            agent_context.metadata["extraction_method"] = "chain_of_thought"
            
            # Convert Pydantic model to dict and store in context for downstream agents
            extracted_dict = extracted.model_dump(mode='json')
            agent_context.extracted_values.update(extracted_dict)
            
            # Process extracted values into template slots for naturalization agent
            slot_values = {}
            
            # Extract field mappings without defaults
            slot_values["is_pediatric"] = extracted_dict.get("is_pediatric")
            slot_values["study_type"] = extracted_dict.get("study_type")
            slot_values["article"] = extracted_dict.get("article")
            slot_values["study_object"] = _normalize_clause(extracted_dict.get("study_object"))
            slot_values["population"] = extracted_dict.get("population")
            slot_values["study_purpose"] = _normalize_clause(
                extracted_dict.get("study_purpose"),
                lower_leading=True,
            )
            slot_values["study_goals"] = _normalize_clause(
                extracted_dict.get("study_goals"),
                lower_leading=True,
            )
            slot_values["key_risks"] = _normalize_clause(
                extracted_dict.get("key_risks"),
                lower_leading=True,
            )
            slot_values["study_duration"] = _normalize_clause(extracted_dict.get("study_duration", ""))  # Keep empty string for duration
            
            # Biospecimen statement
            slot_values["biospecimen_statement"] = (
                _normalize_clause(
                    extracted_dict.get("biospecimen_details"),
                    lower_leading=True,
                )
                if extracted_dict.get("collects_biospecimens") 
                else ""
            )
            
            # Generate benefit statement based on extraction
            benefit_detail = _normalize_clause(
                extracted_dict.get("benefit_description"),
                lower_leading=True,
            )
            if extracted_dict.get("has_direct_benefits"):
                slot_values["benefit_statement"] = CONDITIONAL_TEMPLATES["benefits_personal"].format(
                    benefit_detail=benefit_detail
                )
            else:
                slot_values["benefit_statement"] = CONDITIONAL_TEMPLATES["benefits_others"].format(
                    benefit_detail=benefit_detail
                )
            
            # Randomization text
            if extracted_dict.get("has_randomization"):
                study_obj = (extracted_dict.get("study_object") or "").lower()
                if "device" in study_obj:
                    slot_values["randomization_text"] = CONDITIONAL_TEMPLATES["randomization_device"]
                elif "procedure" in study_obj:
                    slot_values["randomization_text"] = CONDITIONAL_TEMPLATES["randomization_procedure"]
                else:
                    slot_values["randomization_text"] = CONDITIONAL_TEMPLATES["randomization"]
            else:
                slot_values["randomization_text"] = ""
            
            # Alternatives
            if extracted_dict.get("affects_treatment") and extracted_dict.get("alternative_options"):
                alternatives = _normalize_clause(
                    extracted_dict["alternative_options"],
                    lower_leading=True,
                )
                slot_values["alternatives_sentence"] = CONDITIONAL_TEMPLATES["alternatives"].format(
                    alternative_options=alternatives
                )
            else:
                slot_values["alternatives_sentence"] = ""
            
            # Ensure critical template variables are set to prevent rendering errors
            # Only set empty strings for fields that templates require
            slot_values.setdefault("randomization_text", "")
            slot_values.setdefault("washout_text", "")
            slot_values.setdefault("benefit_statement", "")
            slot_values.setdefault(
                "study_duration",
                _normalize_clause(extracted_dict.get("study_duration", "")),
            )
            
            # Handle washout text
            if extracted_dict.get("requires_washout"):
                slot_values["washout_text"] = "You may need to stop taking certain medications before joining this study. "
            else:
                slot_values["washout_text"] = ""
            
            # Store in generated_content for naturalization agent
            agent_context.generated_content = slot_values
            
            return {
                "status": "success",
                "extracted": extracted_dict,
                "extraction_method": "chain_of_thought"
            }
            
        except Exception as e:
            logger.error(f"Chain-of-thought extraction failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "extraction_method": "chain_of_thought"
            }


class KINaturalizationAgent(BaseAgent):
    """Agent that massages extracted slot values to flow with templates using the LLM."""

    def __init__(self):
        super().__init__("KINaturalizationAgent", AgentRole.GENERATOR)
        self.extractor = UnifiedExtractor()

    async def process(self, agent_context: AgentContext) -> Dict[str, Any]:
        self.context = agent_context

        extracted = agent_context.extracted_values or {}
        # Start with existing generated content from _extract_template_values
        generated = agent_context.generated_content or {}

        document_context = ""
        params = agent_context.parameters
        if 'document' in params:
            doc = params['document']
            document_context = doc.text if hasattr(doc, 'text') else str(doc)
        elif 'document_context' in params:
            document_context = params['document_context']
        elif 'document_text' in params:
            document_context = params['document_text']

        # Build a prompt to naturalize slots with structured reasoning
        import json
        system_prompt = (
            "You refine extracted phrases so they fit into a Key Information template. "
            "Provide your reasoning for each refinement to ensure accuracy. "
            "Preserve clinical terms exactly as written in the source. "
            "Return concise clauses that flow naturally when embedded in sentences. "
            "\n\nReasoning approach:\n"
            "1. For each field, explain why you're making specific changes\n"
            "2. Note any clinical terms that must be preserved exactly\n"
            "3. Explain how you're ensuring the text flows naturally\n\n"
            "Output STRICT JSON only, with the following keys, and no extra text.\n\n"
            "Rules per key:\n"
            "- study_purpose: concise clause, no leading 'to', no trailing punctuation.\n"
            "- study_goals: concise clause, no leading 'to', no trailing punctuation.\n"
            "- biospecimen_statement: short phrase starting with a capital letter; no trailing punctuation; "
            "  use only if biospecimens are collected, otherwise return empty string.\n"
            "- study_duration: exact phrase from document (e.g., '6 months', 'up to 2 years'); "
            "  if not present, return empty string (do not invent).\n"
            "- key_risks: main risks in a concise phrase (e.g., 'pain, bleeding, infection').\n"
            "- benefit_description: describe benefits concisely.\n"
        )

        # Provide both doc context and the raw extracted values as source material.
        user_prompt = (
            "Document excerpt:\n" + (document_context[:6000] if document_context else "") +
            "\n\nExtracted values (JSON):\n" + json.dumps(extracted, ensure_ascii=False) +
            "\n\nReturn JSON with keys: study_purpose, study_goals, biospecimen_statement, study_duration, key_risks, benefit_description."
        )

        # Ask LLM to produce JSON
        try:
            response = await self.extractor.complete(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=400,
                temperature=0.1
            )
            # Parse JSON from response
            try:
                polished = json.loads(response)
            except json.JSONDecodeError:
                import re
                m = re.search(r"\{[\s\S]*\}", response)
                polished = json.loads(m.group(0)) if m else {}
        except (json.JSONDecodeError, AttributeError):
            # If all JSON parsing attempts fail, use empty dict
            polished = {}

        # Merge polished values back into generated slots, but only if non-empty
        lower_leading_keys = {"study_purpose", "study_goals", "biospecimen_statement", "key_risks"}
        for key in ["study_purpose", "study_goals", "biospecimen_statement", "study_duration", "key_risks"]:
            val = polished.get(key)
            if isinstance(val, str):
                sval = _normalize_clause(val, lower_leading=key in lower_leading_keys)
                if sval:
                    generated[key] = sval
        
        # Map benefit_description to the already-generated benefit_statement if needed
        benefit_description = polished.get("benefit_description")
        if isinstance(benefit_description, str):
            benefit_text = _normalize_clause(benefit_description, lower_leading=True)
            # Don't override the formatted benefit_statement from conditional templates
            if benefit_text and ("benefit_statement" not in generated or not generated["benefit_statement"]):
                generated["benefit_statement"] = benefit_text

        # Enforce biospecimen presence constraint
        if not extracted.get("collects_biospecimens"):
            generated["biospecimen_statement"] = ""

        agent_context.generated_content = generated
        return {"generated_content": generated}


class InformedConsentPlugin(DocumentPlugin):
    """Plugin for Informed Consent Key Information Summary generation"""
    
    def __init__(self):
        self.plugin_id = "informed-consent-ki"
        self.extraction_agent = KIExtractionAgent()
        self.naturalization_agent = KINaturalizationAgent()
        self.agents = [self.extraction_agent, self.naturalization_agent]
        self.sections = [
            "section1", "section2", "section3", "section4", 
            "section5", "section6", "section7", "section8", "section9"
        ]
    
    def get_plugin_info(self) -> Dict[str, Any]:
        return {
            "id": self.plugin_id,
            "name": "Informed Consent Key Information Summary",
            "version": "5.0.0",
            "description": "Generates IRB-compliant Key Information summaries with optimized extraction",
            "author": "Clinical Research Team",
            "supported_types": ["informed-consent", "consent-form", "irb-consent"],
            "templates": self.sections,
            "features": [
                "Optimized JSON extraction",
                "Azure OpenAI GPT-4o integration",
                "KI-specific extraction schema",
                "9-section Key Information generation",
                "Pediatric language adaptation",
                "IRB compliance validation"
            ]
        }
    
    def get_template_catalog(self) -> TemplateCatalog:
        templates = {}
        for section in self.sections:
            templates[section] = f"informed-consent/sections/{section}.j2"
        templates["main"] = "informed-consent/ki-summary.j2"
        
        return TemplateCatalog(
            templates=templates,
            default_template="main",
            metadata={
                "sections_count": 9,
                "irb_compliant": True,
                "supports_pediatric": True,
                "llm_powered": True,
                "extraction_optimized": True
            }
        )
    
    def get_specialized_agents(self) -> List[Any]:
        return self.agents
    
    def get_validation_rules(self) -> ValidationRuleSet:
        return ValidationRuleSet(
            required_fields=[],
            max_lengths={
                "study_object": 150,
                "study_purpose": 100,
                "study_goals": 100,
                "key_risks": 150,
                "benefit_description": 100,
                "study_duration": 50,
                "alternative_options": 100,
                "biospecimen_details": 100
            },
            allowed_values={
                "study_type": ["studying", "collecting"],
                "article": ["a ", "a new ", ""],
                "population": ["people", "large numbers of people", "small numbers of people",
                              "children", "large numbers of children", "small numbers of children"]
            },
            custom_validators=[],
            intent_critical_fields=["study_object", "key_risks", "study_duration"]
        )
    
    def supports_document_type(self, doc_type: str) -> bool:
        """Check if this plugin supports the given document type"""
        supported = ["informed-consent", "consent-form", "irb-consent", "informed-consent-ki"]
        return doc_type.lower() in supported
    
    def get_sub_template_rules(self) -> Dict[str, Any]:
        """Return rules for sub-template selection"""
        return {
            "pediatric": {
                "condition": "is_pediatric == true",
                "template": "eligibility_children"
            },
            "adult": {
                "condition": "is_pediatric == false", 
                "template": "eligibility_adults"
            }
        }
    
    def get_critical_values(self) -> List[str]:
        """Return list of critical values that must be preserved"""
        return ["study_object", "key_risks", "study_duration", "study_purpose"]
    
    def resolve_template(self, parameters: Dict[str, Any]) -> str:
        """Resolve which template to use based on parameters"""
        # For KI summaries, always use the main template
        return "informed-consent/ki-summary.j2"
