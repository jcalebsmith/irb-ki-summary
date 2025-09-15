"""
Simplified Azure OpenAI Client
Clean implementation using OpenAI SDK best practices
"""
from typing import Dict, Any, Type, Optional
from pydantic import BaseModel
from openai import AsyncAzureOpenAI
from app.config import AZURE_OPENAI_CONFIG
from app.core.exceptions import LLMError
from app.logger import get_logger

logger = get_logger("core.llm_client")


class SimpleLLMClient:
    """
    Simplified Azure OpenAI client with clean interface.
    Reduces from 406 lines to ~100 lines.
    """
    
    def __init__(self):
        """Initialize Azure OpenAI client from config"""
        self.client = AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_CONFIG["api_key"],
            api_version=AZURE_OPENAI_CONFIG["api_version"],
            azure_endpoint=AZURE_OPENAI_CONFIG["endpoint"],
            default_headers=AZURE_OPENAI_CONFIG.get("default_headers", {}),
        )
        self.model = AZURE_OPENAI_CONFIG.get("deployment_name", "gpt-4o")
        self.temperature = AZURE_OPENAI_CONFIG.get("temperature", 0.0)
    
    async def extract(self,
                     document: str,
                     schema: Type[BaseModel],
                     system_prompt: Optional[str] = None) -> BaseModel:
        """
        Extract structured data from document using Pydantic schema.
        
        Args:
            document: Document text to extract from
            schema: Pydantic model defining output structure
            system_prompt: Optional custom system prompt
            
        Returns:
            Instance of the Pydantic model with extracted data
        """
        # Default chain-of-thought prompt for extraction
        if not system_prompt:
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
            {"role": "user", "content": f"Extract information from this document:\n\n{document[:12000]}"}
        ]
        
        try:
            # Use beta.parse for structured outputs with Pydantic
            response = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=schema,
                temperature=self.temperature,
                timeout=30,
            )
            
            result = response.choices[0].message.parsed
            
            # Fallback to manual parsing if needed
            if result is None:
                import json
                response_text = response.choices[0].message.content
                result_dict = json.loads(response_text)
                result = schema(**result_dict)
            
            logger.info(f"Successfully extracted {schema.__name__}")
            return result
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            raise LLMError(
                "extraction",
                f"Failed to extract {schema.__name__}: {e}",
                {"schema": schema.__name__}
            )
    
    async def complete(self,
                      prompt: str,
                      system_prompt: Optional[str] = None,
                      max_tokens: int = 500) -> str:
        """
        Generate text completion for any prompt.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum response tokens
            
        Returns:
            Generated text completion
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=max_tokens,
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Completion failed: {e}")
            raise LLMError(
                "completion",
                f"Failed to generate completion: {e}",
                {"prompt_length": len(prompt)}
            )