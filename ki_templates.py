"""
Structured Key Information Templates for Consistent Summary Generation

This module defines a template-with-slots architecture to reduce variability
in KI summary generation. Each section has:
1. Static template text with clear insertion points
2. Specific extraction queries for dynamic content
3. Validation rules for consistency
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class SlotType(Enum):
    """Types of dynamic content slots in templates"""
    BOOLEAN = "boolean"          # Yes/No decision
    EXTRACTED = "extracted"       # Direct extraction from document
    GENERATED = "generated"       # LLM-generated content
    CONDITIONAL = "conditional"   # Content depends on condition


@dataclass
class TemplateSlot:
    """Defines a dynamic content slot in a template"""
    name: str
    slot_type: SlotType
    extraction_query: str
    validation_rules: Dict[str, Any]
    default_value: Optional[str] = None
    max_length: Optional[int] = None


@dataclass
class SectionTemplate:
    """Defines a complete section template with static text and slots"""
    section_id: str
    template_text: str
    slots: List[TemplateSlot]
    fallback_text: Optional[str] = None
    
    def render(self, slot_values: Dict[str, str]) -> str:
        """Render template with provided slot values"""
        result = self.template_text
        for slot in self.slots:
            value = slot_values.get(slot.name, slot.default_value or "")
            # Validate value length if specified
            if slot.max_length and len(value) > slot.max_length:
                value = value[:slot.max_length].rsplit(' ', 1)[0] + "..."
            result = result.replace(f"{{{slot.name}}}", value)
        return result


# Define structured templates for each section
KI_TEMPLATES = {
    "section1": SectionTemplate(
        section_id="section1",
        template_text="{eligibility_full_text}",
        slots=[
            TemplateSlot(
                name="eligibility_full_text",
                slot_type=SlotType.CONDITIONAL,
                extraction_query=(
                    "Are children eligible to participate in this study? "
                    "Look for mentions of age requirements, pediatric participants, "
                    "or parent/guardian consent. Return ONLY 'YES' or 'NO'."
                ),
                validation_rules={"conditional_template": True},
                default_value=(
                    "You may be eligible to take part in a research study. "
                    "This form contains important information that will help you decide "
                    "whether to join the study. Take the time to carefully review this "
                    "information. You should talk to the researchers about the study and "
                    "ask them any questions you have. You may also wish to talk to others "
                    "such as your family, friends, or other doctors about joining this study. "
                    "If you decide to join the study, you will be asked to sign this form "
                    "before you can start study-related activities. Before you do, be sure "
                    "you understand what the research study is about."
                )
            )
        ]
    ),
    
    "section2": SectionTemplate(
        section_id="section2",
        # Static boilerplate text - no slots needed
        template_text=(
            "A research study is different from the regular medical care you receive "
            "from your doctor. Research studies hope to make discoveries and learn "
            "new information about diseases and how to treat them. You should consider "
            "the reasons why you might want to join a research study or why it is not "
            "the best decision for you at this time."
        ),
        slots=[]
    ),
    
    "section3": SectionTemplate(
        section_id="section3",
        # Static boilerplate text - no slots needed
        template_text=(
            "Research studies do not always offer the possibility of treating your "
            "disease or condition. Research studies also have different kinds of risks "
            "and risk levels, depending on the type of the study. You may also need to "
            "think about other requirements for being in the study. For example, some "
            "studies require you to travel to scheduled visits at the study site in "
            "Ann Arbor or elsewhere. This may require you to arrange travel, change "
            "work schedules, find child care, or make other plans. In your decision "
            "to participate in this study, consider all of these matters carefully."
        ),
        slots=[]
    ),
    
    "section4": SectionTemplate(
        section_id="section4",
        template_text=(
            "This research is {study_type} {article}{study_object} in {population}. "
            "The purpose is to {study_purpose}. This study will {study_goals}. "
            "Your health-related information will be collected during this research. "
            "{biospecimen_statement}"
        ),
        slots=[
            TemplateSlot(
                name="study_type",
                slot_type=SlotType.EXTRACTED,
                extraction_query=(
                    "Is this study primarily studying/testing something or "
                    "collecting/gathering something? Return ONLY 'studying' or 'collecting'."
                ),
                validation_rules={"allowed_values": ["studying", "collecting"]},
                default_value="studying"
            ),
            TemplateSlot(
                name="article",
                slot_type=SlotType.EXTRACTED,
                extraction_query=(
                    "What article should precede the study object? Consider: "
                    "- 'a ' for existing/standard items (e.g., 'a drug', 'a device') "
                    "- 'a new ' for novel/investigational items (e.g., 'a new drug', 'a new procedure') "
                    "- '' (empty string) for plural/uncountable nouns (e.g., 'information', 'biospecimens') "
                    "Return ONLY 'a ', 'a new ', or '' (empty string)."
                ),
                validation_rules={"allowed_values": ["a ", "a new ", ""]},
                default_value="a "
            ),
            TemplateSlot(
                name="study_object",
                slot_type=SlotType.EXTRACTED,
                extraction_query=(
                    "What is the main object being studied? (e.g., 'drug', 'device', 'procedure', "
                    "'information', 'biospecimens', 'behavioral change', 'diagnostic tool'). "
                    "Include FDA approval status if mentioned (e.g., 'drug already approved by the FDA for treating cancer'). "
                    "Provide the complete description in lowercase."
                ),
                validation_rules={"max_words": 20},
                max_length=150
            ),
            TemplateSlot(
                name="population",
                slot_type=SlotType.EXTRACTED,
                extraction_query=(
                    "What population will participate? Return one of: 'people', "
                    "'large numbers of people', 'small numbers of people', 'children', "
                    "'large numbers of children', 'small numbers of children'."
                ),
                validation_rules={"max_words": 5},
                default_value="people"
            ),
            TemplateSlot(
                name="study_purpose",
                slot_type=SlotType.GENERATED,
                extraction_query=(
                    "In 10-15 words, what is the main purpose of this study? "
                    "Use simple language. Do not include phrases like 'The purpose is' or "
                    "'The study's main purpose is' - just state the purpose directly."
                ),
                validation_rules={"max_words": 15},
                max_length=100
            ),
            TemplateSlot(
                name="study_goals",
                slot_type=SlotType.GENERATED,
                extraction_query=(
                    "In 10-15 words, what will this study accomplish or measure? "
                    "Use simple language. Do not include phrases like 'The study will' - "
                    "just state what it will accomplish directly."
                ),
                validation_rules={"max_words": 15},
                max_length=100
            ),
            TemplateSlot(
                name="biospecimen_statement",
                slot_type=SlotType.CONDITIONAL,
                extraction_query=(
                    "Will biological specimens (blood, tissue, DNA, etc.) be collected? "
                    "If yes, provide a brief statement about what will be collected. "
                    "If no, return empty string."
                ),
                validation_rules={"max_words": 20},
                default_value=""
            )
        ]
    ),
    
    "section5": SectionTemplate(
        section_id="section5",
        template_text="{randomization_text}{washout_text}",
        slots=[
            TemplateSlot(
                name="randomization_text",
                slot_type=SlotType.CONDITIONAL,
                extraction_query=(
                    "Does the document contain the exact words 'randomize', "
                    "'randomization', or 'randomized'? Return 'YES' or 'NO'."
                ),
                validation_rules={"conditional_template": True},
                default_value=""
            ),
            TemplateSlot(
                name="washout_text",
                slot_type=SlotType.CONDITIONAL,
                extraction_query=(
                    "Does the study require stopping medications before or during "
                    "participation? Return 'YES' or 'NO'."
                ),
                validation_rules={"conditional_template": True},
                default_value=""
            )
        ]
    ),
    
    "section6": SectionTemplate(
        section_id="section6",
        template_text=(
            "There can be risks associated with joining any research study. "
            "The type of risk may impact whether you decide to join the study. "
            "For this study, some of these risks may include {key_risks}. "
            "More detailed information will be provided later in this document."
        ),
        slots=[
            TemplateSlot(
                name="key_risks",
                slot_type=SlotType.GENERATED,
                extraction_query=(
                    "Briefly describe the 2-3 most important risks from participating in this study "
                    "(not standard care risks). Focus on risks causing pain or distress. "
                    "Use a tone of calm confidence, maximum 30 words total."
                ),
                validation_rules={"max_words": 30},
                max_length=150
            )
        ]
    ),
    
    "section7": SectionTemplate(
        section_id="section7",
        template_text=(
            "{benefit_statement}. More information will be provided later in this document."
        ),
        slots=[
            TemplateSlot(
                name="benefit_statement",
                slot_type=SlotType.CONDITIONAL,
                extraction_query=(
                    "Are there meaningful direct personal benefits to participants? "
                    "Return 'YES' or 'NO'."
                ),
                validation_rules={"conditional_template": True},
                default_value="NO"
            ),
            TemplateSlot(
                name="benefit_detail",
                slot_type=SlotType.GENERATED,
                extraction_query=(
                    "Briefly summarize the benefits based on what you have learned about this research study. "
                    "Complete this phrase: 'by [your text here]'. Do not include 'by' in your response. "
                    "Make sure the text fits grammatically with the sentence and doesn't repeat information. "
                    "Maximum 20 words."
                ),
                validation_rules={"max_words": 20},
                max_length=100
            )
        ]
    ),
    
    "section8": SectionTemplate(
        section_id="section8",
        template_text="The study will take {study_duration}.",
        slots=[
            TemplateSlot(
                name="study_duration",
                slot_type=SlotType.EXTRACTED,
                extraction_query=(
                    "How long will participants be in the study? "
                    "Provide a brief answer (e.g., '6 months', 'up to 2 years'). "
                    "Maximum 10 words."
                ),
                validation_rules={"max_words": 10},
                max_length=50
            )
        ]
    ),
    
    "section9": SectionTemplate(
        section_id="section9",
        template_text=(
            "{alternatives_sentence}"
            "Even if you decide to join the study now, you are free to leave "
            "at any time if you change your mind."
        ),
        slots=[
            TemplateSlot(
                name="alternatives_sentence",
                slot_type=SlotType.CONDITIONAL,
                extraction_query=(
                    "Does participating in the study affect current or future treatment/care options? "
                    "Return 'YES' or 'NO'."
                ),
                validation_rules={"conditional_template": True},
                default_value=""
            ),
            TemplateSlot(
                name="alternative_options",
                slot_type=SlotType.GENERATED,
                extraction_query=(
                    "If the study affects treatment options, briefly specify potential "
                    "treatment/care alternatives such as the current standard of care. "
                    "Maximum 20 words."
                ),
                validation_rules={"max_words": 20},
                max_length=100,
                default_value=""
            )
        ]
    )
}


# Conditional text templates for sections that need them
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


def validate_slot_value(slot: TemplateSlot, value: str) -> tuple[bool, str]:
    """
    Validate a slot value against its rules
    Returns (is_valid, error_message)
    """
    if not value and slot.default_value:
        return True, ""
    
    rules = slot.validation_rules
    
    # Check allowed values
    if "allowed_values" in rules:
        if value.upper() not in [v.upper() for v in rules["allowed_values"]]:
            return False, f"Value must be one of: {rules['allowed_values']}"
    
    # Check word count
    if "max_words" in rules:
        word_count = len(value.split())
        if word_count > rules["max_words"]:
            return False, f"Exceeds maximum {rules['max_words']} words"
    
    # Check length
    if slot.max_length and len(value) > slot.max_length:
        return False, f"Exceeds maximum {slot.max_length} characters"
    
    return True, ""