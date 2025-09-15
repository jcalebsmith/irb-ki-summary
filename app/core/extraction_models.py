"""
Pydantic models for structured extraction
Defines strongly-typed models for extracting information from documents
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal, Dict, Any
from enum import Enum
import re


class ReasoningStep(BaseModel):
    """Represents a single step in chain-of-thought reasoning"""
    field: str = Field(description="The field being extracted")
    explanation: str = Field(description="Explanation of where we're looking and why")
    evidence: Optional[str] = Field(default=None, description="Relevant text found in document")
    interpretation: str = Field(description="How we interpret the evidence")
    decision: Any = Field(description="Final value decided for this field")


class ExtractionReasoning(BaseModel):
    """Container for extraction reasoning steps"""
    steps: List[ReasoningStep] = Field(default_factory=list, description="Chain-of-thought reasoning steps")
    extraction: Optional[Dict[str, Any]] = Field(default=None, description="Final extracted values")


class StudyType(str, Enum):
    """Types of studies"""
    STUDYING = "studying"
    COLLECTING = "collecting"


class ArticleType(str, Enum):
    """Article types for study objects"""
    A = "a "
    A_NEW = "a new "
    NONE = ""


class PopulationType(str, Enum):
    """Population types for studies"""
    PEOPLE = "people"
    LARGE_NUMBERS_PEOPLE = "large numbers of people"
    SMALL_NUMBERS_PEOPLE = "small numbers of people"
    CHILDREN = "children"
    LARGE_NUMBERS_CHILDREN = "large numbers of children"
    SMALL_NUMBERS_CHILDREN = "small numbers of children"


class KIExtractionSchema(BaseModel):
    """
    Schema for extracting Key Information from Informed Consent documents
    All fields have strict validation and word limits
    """
    # Section 1 - Eligibility
    is_pediatric: bool = Field(
        description="Are children eligible to participate? Look for age requirements, pediatric participants, or parent/guardian consent."
    )
    
    # Section 4 - Study Description  
    study_type: StudyType = Field(
        description="Is this study primarily studying/testing something or collecting/gathering something?"
    )
    
    article: ArticleType = Field(
        description="What article should precede the study object? 'a ' for existing, 'a new ' for novel, '' for plural/uncountable"
    )
    
    study_object: str = Field(
        max_length=150,
        description="Main object being studied (e.g., drug, device, procedure). Include FDA status if mentioned. Lowercase. Max 30 words."
    )
    
    population: PopulationType = Field(
        description="What population will participate?"
    )
    
    study_purpose: str = Field(
        max_length=100,
        description="Main purpose of study in 10-15 words. Simple language, no intro phrases."
    )
    
    study_goals: str = Field(
        max_length=100,
        description="What study will accomplish in 10-15 words. Simple language, direct statement."
    )
    
    # Section 5 - Randomization and Washout
    has_randomization: bool = Field(
        description="Does document contain words 'randomize', 'randomization', or 'randomized'?"
    )
    
    requires_washout: bool = Field(
        description="Does study require stopping medications before/during participation?"
    )
    
    # Section 6 - Risks
    key_risks: str = Field(
        max_length=150,
        description="2-3 most important risks from study (not standard care). Focus on pain/distress. 30 words max."
    )
    
    # Section 7 - Benefits
    has_direct_benefits: bool = Field(
        description="Are there meaningful direct personal benefits to participants?"
    )
    
    benefit_description: str = Field(
        max_length=100,
        description="Benefits summary to complete 'by [text]'. Don't include 'by'. 20 words max."
    )
    
    # Section 8 - Duration
    study_duration: str = Field(
        default="",
        max_length=50,
        description="Step 1: Search for duration statements near keywords: 'duration', 'last', 'participate for', 'involvement', 'study period', 'treatment period', 'follow-up'. Step 2: Extract the EXACT time phrase (e.g., '6 months', 'up to 2 years', '12 weeks'). Step 3: Return empty string if not found. NEVER use placeholders."
    )
    
    @field_validator('study_duration')
    @classmethod
    def validate_duration(cls, v: str) -> str:
        """Validate study duration is a real duration, not a placeholder"""
        if not v:
            return v
        
        # Use existing text processing utilities
        from app.core.utils import TextProcessingUtils
        cleaned = TextProcessingUtils.clean_whitespace(v).lower()
        
        # Simplified placeholder check
        placeholders = {'not specified', 'unknown', 'varies', 'the study period', 'tbd', 'n/a'}
        if cleaned in placeholders:
            return ""
        
        # Simplified pattern check
        return v if re.search(r'\d+\s*\w+', cleaned) else ""
    
    # Section 9 - Alternatives
    affects_treatment: bool = Field(
        description="Does participation affect current/future treatment options?"
    )
    
    alternative_options: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Treatment alternatives if study affects options. 20 words max."
    )
    
    # Additional fields
    collects_biospecimens: bool = Field(
        description="Will biological specimens (blood, tissue, DNA, etc.) be collected?"
    )
    
    biospecimen_details: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Brief statement about what specimens will be collected. 20 words max."
    )


class ClinicalProtocolExtractionSchema(BaseModel):
    """
    Schema for extracting information from Clinical Protocol documents
    """
    protocol_title: str = Field(
        description="Full title of the clinical protocol"
    )
    
    protocol_number: str = Field(
        description="Protocol number or identifier"
    )
    
    sponsor: str = Field(
        description="Study sponsor organization"
    )
    
    phase: Optional[str] = Field(
        default=None,
        description="Clinical trial phase (e.g., Phase 1, Phase 2, Phase 3)"
    )
    
    primary_endpoint: str = Field(
        description="Primary study endpoint"
    )
    
    secondary_endpoints: List[str] = Field(
        default_factory=list,
        description="List of secondary endpoints"
    )
    
    inclusion_criteria: List[str] = Field(
        default_factory=list,
        description="Key inclusion criteria"
    )
    
    exclusion_criteria: List[str] = Field(
        default_factory=list,
        description="Key exclusion criteria"
    )
    
    study_design: str = Field(
        description="Study design (e.g., randomized, double-blind, placebo-controlled)"
    )
    
    sample_size: Optional[int] = Field(
        default=None,
        description="Target sample size"
    )
    
    study_duration: str = Field(
        description="Total study duration"
    )
    
    regulatory_section: Literal["device", "drug", "biologic"] = Field(
        description="Type of regulatory section"
    )
    
    therapeutic_area: str = Field(
        description="Therapeutic area (e.g., cardiovascular, oncology)"
    )


class GenericExtractionSchema(BaseModel):
    """
    Generic schema for document extraction when specific schema is not available
    """
    title: Optional[str] = Field(
        default=None,
        description="Document title if present"
    )
    
    summary: str = Field(
        description="Brief summary of the document"
    )
    
    key_points: List[str] = Field(
        default_factory=list,
        description="Key points extracted from the document"
    )
    
    entities: List[str] = Field(
        default_factory=list,
        description="Important entities mentioned (people, organizations, etc.)"
    )
    
    dates: List[str] = Field(
        default_factory=list,
        description="Important dates mentioned"
    )
    
    numbers: List[str] = Field(
        default_factory=list,
        description="Important numbers or statistics mentioned"
    )