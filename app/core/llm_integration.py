"""
Generic Azure OpenAI Integration with Structured Outputs
Provides base LLM functionality with Pydantic model support
"""
import os
import json
from typing import Dict, Any, List, Optional, Union, Type, Tuple
from dotenv import load_dotenv
from pathlib import Path
from pydantic import BaseModel
from openai import AzureOpenAI
from app.core.exceptions import LLMError, ExtractionError
from app.core.llm_validation import (
    LLMSelfHealingExtractor,
    DocumentValidationResult
)

# Load environment variables from app/.env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class GenericLLMExtractor:
    """
    Generic Azure OpenAI client for document extraction
    """
    
    def __init__(self):
        """Initialize Azure OpenAI client"""
        from app.config import AZURE_OPENAI_CONFIG
        
        # Use AzureOpenAI client with proper configuration
        self.client = AzureOpenAI(
            api_key=AZURE_OPENAI_CONFIG["api_key"],
            api_version=AZURE_OPENAI_CONFIG["api_version"],
            azure_endpoint=AZURE_OPENAI_CONFIG["endpoint"],
            default_headers=AZURE_OPENAI_CONFIG["default_headers"],
        )
        # Use gpt-4o as the deployment name
        self.model = "gpt-4o"
        self.temperature = AZURE_OPENAI_CONFIG["temperature"]
        
        self.deployment = os.getenv("DEPLOYMENT_ID", "gpt-4o")
    
    async def extract_structured(self,
                                document_context: str,
                                output_cls: Type[BaseModel],
                                system_prompt: str = None) -> BaseModel:
        """
        Extract structured data using Pydantic models with guaranteed schema compliance
        
        Args:
            document_context: Document text to extract from
            output_cls: Pydantic model class defining the output structure
            system_prompt: Optional custom system prompt
            
        Returns:
            Instance of the Pydantic model with extracted data
        """
        import asyncio
        
        # Simple retry with exponential backoff
        for attempt in range(3):
            try:
                # Create JSON schema from Pydantic model
                schema = output_cls.model_json_schema()
                
                # Build system prompt with schema
                if not system_prompt:
                    system_prompt = (
                        "You are an expert at extracting structured information from documents. "
                        "Extract the requested information accurately and concisely. "
                        "You must return valid JSON that matches this schema:\n\n"
                        f"{json.dumps(schema, indent=2)}\n\n"
                        "Follow the schema requirements strictly and ensure all required fields are present."
                    )
                
                # Build messages for Azure OpenAI SDK
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract information from this document and return as JSON:\n\n{document_context[:12000]}"}
                ]
                
                # Get structured response using chat.completions.create
                print(f"DEBUG: Calling Azure OpenAI API with model={self.model}", flush=True)
                
                # Use chat.completions.create with JSON response format
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=self.temperature,
                    timeout=30,  # Add 30 second timeout
                )
                print("DEBUG: Azure OpenAI API call completed", flush=True)
                
                # Parse the JSON response
                response_text = response.choices[0].message.content
                result_dict = json.loads(response_text)
                result = output_cls(**result_dict)
                
                return result
                
            except Exception as e:
                if attempt == 2:  # Last attempt
                    raise LLMError(
                        "structured_extraction",
                        f"Failed to extract structured data after 3 attempts: {e}",
                        {"output_class": output_cls.__name__}
                    )
                await asyncio.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s
    
    async def extract_structured_with_validation(self,
                                                document_context: str,
                                                output_cls: Type[BaseModel],
                                                validate: bool = True,
                                                max_attempts: int = 3) -> Tuple[BaseModel, Optional[DocumentValidationResult]]:
        """
        Extract structured data with semantic validation and self-healing
        
        Args:
            document_context: Document text to extract from
            output_cls: Pydantic model class defining the output structure
            validate: Whether to perform semantic validation
            max_attempts: Maximum extraction attempts for self-healing
            
        Returns:
            Tuple of (extracted model, validation result if validate=True)
        """
        if not validate:
            # Standard extraction without validation
            result = await self.extract_structured(document_context, output_cls)
            return result, None
        
        # Use LLM-based self-healing extractor with validation
        healer = LLMSelfHealingExtractor(self, max_attempts=max_attempts)
        extraction, validation = await healer.extract_with_validation(
            document_context=document_context,
            output_cls=output_cls
        )
        
        return extraction, validation
    
    async def extract_json(self, 
                          document_context: str,
                          extraction_schema: Dict[str, Any],
                          system_prompt: str = None) -> Dict[str, Any]:
        """
        Legacy JSON extraction - now uses structured extraction internally
        
        Args:
            document_context: Document text to extract from
            extraction_schema: Dictionary describing what to extract
            system_prompt: Optional custom system prompt
            
        Returns:
            Dictionary with extracted values
        """
        # Check if we have a Pydantic model available
        from app.core.extraction_models import KIExtractionSchema
        
        # For KI extraction, use the Pydantic model
        if "is_pediatric" in extraction_schema and "study_type" in extraction_schema:
            try:
                result = await self.extract_structured(
                    document_context=document_context,
                    output_cls=KIExtractionSchema,
                    system_prompt=system_prompt
                )
                # Convert Pydantic model to dict
                return result.model_dump()
            except LLMError:
                # Structured extraction failed, continue with fallback
                pass
        
        # Fallback to old method for other schemas
        try:
            # Build system prompt
            if not system_prompt:
                system_prompt = (
                    "You are an expert at extracting structured information from documents. "
                    "Extract the requested information accurately and concisely. "
                    "Return a valid JSON object with all requested fields."
                )
            
            # Build user prompt with schema
            user_prompt = (
                f"Extract the following information from this document:\n\n"
                f"Required fields:\n{json.dumps(extraction_schema, indent=2)}\n\n"
                f"Document:\n{document_context[:8000]}"
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Use OpenAI SDK for chat completion
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
            )
            
            # Parse response
            response_text = response.choices[0].message.content
            
            # Use utility for JSON extraction
            from app.core.utils import JSONUtils
            result = JSONUtils.extract_json_from_text(response_text)
            if result is None:
                print(f"Could not parse JSON from response: {response_text[:200]}")
                return {"error": "Failed to parse JSON"}
            
            return result
            
        except json.JSONDecodeError as e:
            raise ExtractionError(
                f"Failed to parse JSON response: {str(e)}",
                details={"response": response_text[:200] if 'response_text' in locals() else None}
            )
        except Exception as e:
            raise LLMError(
                "json_extraction",
                f"Failed to extract JSON: {str(e)}",
                {"schema": extraction_schema}
            )
    
    async def extract_text(self, 
                          document_context: str,
                          query: str,
                          max_words: int = 50) -> str:
        """
        Extract specific text based on a query
        
        Args:
            document_context: Document to extract from
            query: What to extract
            max_words: Maximum words in response
            
        Returns:
            Extracted text string
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": f"Extract the requested information in {max_words} words or less."
                },
                {
                    "role": "user",
                    "content": f"{query}\n\nDocument:\n{document_context[:4000]}"
                }
            ]
            
            # Use OpenAI SDK for chat completion
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
            )
            
            result = response.choices[0].message.content.strip()
            return result
            
        except Exception as e:
            raise LLMError(
                "text_extraction",
                f"Failed to extract text: {str(e)}",
                {"query": query, "max_words": max_words}
            )
    
    async def extract_boolean(self,
                            document_context: str,
                            query: str) -> bool:
        """
        Extract a yes/no answer based on a query
        
        Args:
            document_context: Document to analyze
            query: Yes/no question about the document
            
        Returns:
            Boolean result
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": "Answer the question with only 'YES' or 'NO' based on the document."
                },
                {
                    "role": "user",
                    "content": f"{query}\n\nDocument:\n{document_context[:4000]}"
                }
            ]
            
            # Use OpenAI SDK for chat completion
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
            )
            
            answer = response.choices[0].message.content.strip().upper()
            result = answer == "YES"
            return result
            
        except Exception as e:
            raise LLMError(
                "boolean_extraction",
                f"Failed to extract boolean value: {str(e)}",
                {"query": query}
            )
    
    async def extract_enum(self,
                         document_context: str,
                         query: str,
                         allowed_values: List[str]) -> str:
        """
        Extract a value from a list of allowed options
        
        Args:
            document_context: Document to analyze
            query: What to determine
            allowed_values: List of valid options
            
        Returns:
            One of the allowed values
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"Based on the document, select the most appropriate option from: "
                        f"{', '.join(allowed_values)}. Return only the selected option."
                    )
                },
                {
                    "role": "user",
                    "content": f"{query}\n\nDocument:\n{document_context[:4000]}"
                }
            ]
            
            # Use OpenAI SDK for chat completion
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
            )
            
            result = response.choices[0].message.content.strip()
            # Validate it's in allowed values
            if result not in allowed_values and allowed_values:
                result = allowed_values[0]  # Default to first option
            
            return result
            
        except Exception as e:
            raise LLMError(
                "enum_extraction",
                f"Failed to extract enum value: {str(e)}",
                {"query": query, "allowed_values": allowed_values}
            )
    
    async def complete(self,
                      prompt: str,
                      system_prompt: str = None,
                      max_tokens: int = 500,
                      temperature: float = 0.1) -> str:
        """
        Generic completion for any prompt
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum response tokens
            temperature: Sampling temperature
            
        Returns:
            Completion text
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Use OpenAI SDK for chat completion
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise LLMError(
                "completion",
                f"Failed to generate completion: {str(e)}",
                {"prompt_length": len(prompt), "temperature": temperature}
            )
    


def get_generic_extractor() -> GenericLLMExtractor:
    """Create a new generic extractor instance"""
    return GenericLLMExtractor()