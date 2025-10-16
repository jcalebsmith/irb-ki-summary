"""
Unified Document Extraction Module

Single, simple implementation using only structured extraction with chain of thought.
Replaces 7 different extractors with one clean method.
"""

import json
import os
import re
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel

from app.config import AZURE_OPENAI_CONFIG
from app.core.extraction_models import KIExtractionSchema
from app.logger import get_logger
from openai import AsyncAzureOpenAI

logger = get_logger(__name__)

T = TypeVar('T', bound=BaseModel)


def _parse_structured_fields(text: str) -> Dict[str, str]:
    """Parse simple KEY: value pairs from a document string."""
    fields: Dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip().lower()] = value.strip()
    return fields


def _bool_from_field(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in {"true", "yes", "1", "y"}:
        return True
    if lowered in {"false", "no", "0", "n"}:
        return False
    return default


def _limit_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).strip()


def _first_sentence_with_keyword(text: str, keyword: str) -> str:
    sentences = re.split(r"[.!?]\s+", text)
    for sentence in sentences:
        if keyword.lower() in sentence.lower():
            return sentence.strip()
    return ""


def _find_duration_phrase(text: str) -> str:
    match = re.search(
        r"\b(\d+\s+(?:day|days|week|weeks|month|months|year|years))\b",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1).lower()
    return ""


def _offline_ki_payload(document: str) -> Dict[str, Any]:
    """
    Build a deterministic payload for KIExtractionSchema when offline mode is active.
    """
    fields = _parse_structured_fields(document)
    lower_doc = document.lower()

    def normalized(key: str, default: str = "") -> str:
        value = fields.get(key)
        return value.strip() if value else default

    study_type = normalized("study_type", "studying").lower()
    if study_type not in {"studying", "collecting"}:
        study_type = "studying"

    article = normalized("article", "a ").lower()
    if article not in {"a ", "a new ", ""}:
        article = "a "

    population = normalized("population", "")
    if not population:
        if "child" in lower_doc:
            population = "children"
        elif "small number" in lower_doc:
            population = "small numbers of people"
        else:
            population = "people"
    population = population.lower()
    allowed_population = {
        "people",
        "large numbers of people",
        "small numbers of people",
        "children",
        "large numbers of children",
        "small numbers of children",
    }
    if population not in allowed_population:
        population = "people"

    study_object = normalized("study_object", "")
    if not study_object:
        sentence = _first_sentence_with_keyword(document, "study")
        if sentence:
            study_object = _limit_words(sentence, 6).lower()
        if not study_object:
            study_object = "the study treatment"

    study_purpose = normalized("study_purpose", "")
    if not study_purpose:
        purpose_sentence = _first_sentence_with_keyword(document, "purpose") or _first_sentence_with_keyword(document, "goal")
        if purpose_sentence:
            study_purpose = _limit_words(purpose_sentence, 15)
        if not study_purpose:
            study_purpose = "explain the research study"

    study_goals = normalized("study_goals", "")
    if not study_goals:
        goals_sentence = _first_sentence_with_keyword(document, "goal") or _first_sentence_with_keyword(document, "will")
        if goals_sentence:
            study_goals = _limit_words(goals_sentence, 15)
        if not study_goals:
            study_goals = "evaluate the study approach"

    key_risks = normalized("key_risks", "")
    if not key_risks:
        risk_sentence = _first_sentence_with_keyword(document, "risk")
        if risk_sentence:
            key_risks = _limit_words(risk_sentence, 20)
        if not key_risks:
            key_risks = "common study risks such as discomfort or fatigue"

    has_direct_benefits = _bool_from_field(fields.get("has_direct_benefits"))
    if not fields.get("has_direct_benefits"):
        has_direct_benefits = "benefit" in lower_doc or "help" in lower_doc

    benefit_description = normalized("benefit_description", "")
    if not benefit_description:
        benefit_sentence = _first_sentence_with_keyword(document, "benefit") or _first_sentence_with_keyword(document, "help")
        if benefit_sentence:
            benefit_description = _limit_words(benefit_sentence, 15)
        if not benefit_description:
            benefit_description = "help future patients with similar conditions"

    study_duration = normalized("study_duration", "")
    if not study_duration:
        study_duration = _find_duration_phrase(document)
        if not study_duration:
            study_duration = "the study period"

    has_randomization = _bool_from_field(fields.get("has_randomization"))
    if not fields.get("has_randomization"):
        has_randomization = "randomiz" in lower_doc

    requires_washout = _bool_from_field(fields.get("requires_washout"))
    if not fields.get("requires_washout"):
        requires_washout = "washout" in lower_doc or "stop taking" in lower_doc

    affects_treatment = _bool_from_field(fields.get("affects_treatment"))
    if not fields.get("affects_treatment"):
        affects_treatment = "treatment option" in lower_doc or "instead of" in lower_doc

    alternative_options = normalized("alternative_options", "")
    if not alternative_options and affects_treatment:
        alt_sentence = _first_sentence_with_keyword(document, "alternative") or _first_sentence_with_keyword(document, "option")
        if alt_sentence:
            alternative_options = _limit_words(alt_sentence, 15)
        if not alternative_options:
            alternative_options = "standard medical care"

    collects_biospecimens = _bool_from_field(fields.get("collects_biospecimens"))
    if not fields.get("collects_biospecimens"):
        collects_biospecimens = any(keyword in lower_doc for keyword in ["blood", "sample", "biospecimen", "tissue"])

    biospecimen_details = normalized("biospecimen_details", "")
    if (not biospecimen_details) and collects_biospecimens:
        bio_sentence = _first_sentence_with_keyword(document, "blood") or _first_sentence_with_keyword(document, "sample")
        if bio_sentence:
            biospecimen_details = _limit_words(bio_sentence, 15)
        if not biospecimen_details:
            biospecimen_details = "blood samples will be collected"

    payload: Dict[str, Any] = {
        "is_pediatric": _bool_from_field(fields.get("is_pediatric"), default=("child" in lower_doc)),
        "study_type": study_type,
        "article": article,
        "study_object": study_object,
        "population": population,
        "study_purpose": study_purpose,
        "study_goals": study_goals,
        "has_randomization": has_randomization,
        "requires_washout": requires_washout,
        "key_risks": key_risks,
        "has_direct_benefits": has_direct_benefits,
        "benefit_description": benefit_description,
        "study_duration": study_duration,
        "affects_treatment": affects_treatment,
        "alternative_options": alternative_options or None,
        "collects_biospecimens": collects_biospecimens,
        "biospecimen_details": biospecimen_details or None,
    }

    if not payload["affects_treatment"]:
        payload["alternative_options"] = None
    if not payload["collects_biospecimens"]:
        payload["biospecimen_details"] = None

    return payload


def _offline_polished_values(values: Dict[str, Any]) -> Dict[str, Any]:
    """Create naturalized slot values without calling an external LLM."""
    biospecimen = ""
    if values.get("collects_biospecimens") and values.get("biospecimen_details"):
        biospecimen = values["biospecimen_details"]

    return {
        "study_purpose": values.get("study_purpose", ""),
        "study_goals": values.get("study_goals", ""),
        "biospecimen_statement": biospecimen,
        "study_duration": values.get("study_duration", ""),
        "key_risks": values.get("key_risks", ""),
        "benefit_description": values.get("benefit_description", ""),
    }


class UnifiedExtractor:
    """
    Single extractor using ONLY structured extraction with chain of thought.
    Replaces all 7 previous implementations with one simple approach.
    """

    def __init__(self, llm_client: Optional[AsyncAzureOpenAI] = None):
        """
        Initialize the unified extractor.

        Args:
            llm_client: Optional Azure OpenAI client for extraction
        """
        self.offline_mode = bool(os.getenv("USE_OFFLINE_KI_EXTRACTOR"))
        if not self.offline_mode and all(
            [
                AZURE_OPENAI_CONFIG.get("api_key"),
                AZURE_OPENAI_CONFIG.get("endpoint"),
                AZURE_OPENAI_CONFIG.get("api_version"),
            ]
        ):
            self.llm_client = llm_client or self._create_default_client()
        else:
            self.llm_client = None
            self.offline_mode = True

        self.model = AZURE_OPENAI_CONFIG.get("deployment_name", "gpt-4")
        self.temperature = AZURE_OPENAI_CONFIG.get("temperature", 0.0)

    def _create_default_client(self) -> AsyncAzureOpenAI:
        """Create default Azure OpenAI client from config"""
        return AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_CONFIG["api_key"],
            api_version=AZURE_OPENAI_CONFIG["api_version"],
            azure_endpoint=AZURE_OPENAI_CONFIG["endpoint"],
            default_headers=AZURE_OPENAI_CONFIG.get("default_headers", {}),
        )

    async def extract(self, document: str, output_schema: Type[T]) -> T:
        """
        Extract structured data using chain of thought with Pydantic schema.

        Args:
            document: Document text to extract from
            output_schema: Pydantic model defining the output structure

        Returns:
            Instance of the Pydantic model with extracted data
        """
        if self.offline_mode:
            if output_schema is KIExtractionSchema or getattr(output_schema, "__name__", "") == "KIExtractionSchema":
                payload = _offline_ki_payload(document)
                return output_schema(**payload)
            raise NotImplementedError("Offline extraction currently supports only KIExtractionSchema")

        system_prompt = (
            "You are an expert at extracting structured information from documents.\n"
            "Use chain of thought reasoning:\n"
            "1. First, identify the relevant sections in the document\n"
            "2. Extract the requested information accurately\n"
            "3. Verify the extracted values make sense in context\n"
            "4. Return the structured output matching the schema\n\n"
            "Think step-by-step internally, but only return the final structured output."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract information from this document:\n\n{document}"},
        ]

        try:
            schema_prompt = f"\n\nReturn a JSON object matching this schema:\n{output_schema.model_json_schema()}"
            messages[-1]["content"] += schema_prompt

            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=self.temperature,
                timeout=60,
            )

            content = response.choices[0].message.content
            result_dict = json.loads(content)
            result = output_schema(**result_dict)

            logger.info(f"Successfully extracted {output_schema.__name__}")
            return result

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            raise

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 400,
        **kwargs: Any,
    ) -> str:
        """
        Complete a prompt using the configured LLM or an offline fallback.
        """
        if self.offline_mode:
            values = {}
            marker = "Extracted values (JSON):\n"
            if marker in prompt:
                after_marker = prompt.split(marker, 1)[1]
                terminator = "\n\nReturn JSON"
                blob = after_marker.split(terminator, 1)[0] if terminator in after_marker else after_marker
                try:
                    values = json.loads(blob)
                except json.JSONDecodeError:
                    values = {}
            return json.dumps(_offline_polished_values(values))

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        temperature = kwargs.get("temperature", self.temperature)
        requested_max_tokens = kwargs.get("max_tokens", max_tokens)

        response = await self.llm_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=requested_max_tokens,
        )
        return response.choices[0].message.content
