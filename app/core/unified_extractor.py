"""
Unified Document Extraction Module

Single, simple implementation using only structured extraction with chain of thought.
Replaces 7 different extractors with one clean method.
"""

import json
from typing import Optional, Type, TypeVar
from pydantic import BaseModel
from app.logger import get_logger
from app.config import AZURE_OPENAI_CONFIG
from openai import AsyncAzureOpenAI

logger = get_logger(__name__)

T = TypeVar('T', bound=BaseModel)


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
        self.llm_client = llm_client or self._create_default_client()
        self.model = AZURE_OPENAI_CONFIG.get("deployment_name", "gpt-4")
        self.temperature = AZURE_OPENAI_CONFIG.get("temperature", 0.0)
    
    def _create_default_client(self) -> AsyncAzureOpenAI:
        """Create default Azure OpenAI client from config"""
        return AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_CONFIG["api_key"],
            api_version=AZURE_OPENAI_CONFIG["api_version"],
            azure_endpoint=AZURE_OPENAI_CONFIG["endpoint"],
            default_headers=AZURE_OPENAI_CONFIG.get("default_headers", {})
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
        # Chain of thought system prompt
        system_prompt = (
            "You are an expert at extracting structured information from documents.\n"
            "Use chain of thought reasoning:\n"
            "1. First, identify the relevant sections in the document\n"
            "2. Extract the requested information accurately\n"
            "3. Verify the extracted values make sense in context\n"
            "4. Return the structured output matching the schema\n\n"
            "Think step-by-step internally, but only return the final structured output."
        )
        
        # Prepare messages - send entire document, not just first 12k chars
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract information from this document:\n\n{document}"}
        ]
        
        try:
            # Add schema description to the prompt
            schema_prompt = f"\n\nReturn a JSON object matching this schema:\n{output_schema.model_json_schema()}"
            messages[-1]["content"] += schema_prompt
            
            # Use regular completion with JSON mode
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=self.temperature,
                timeout=60
            )
            
            # Parse the JSON response
            content = response.choices[0].message.content
            result_dict = json.loads(content)
            result = output_schema(**result_dict)
            
            logger.info(f"Successfully extracted {output_schema.__name__}")
            return result
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            # Re-raise the exception instead of hiding it with defaults
            raise
