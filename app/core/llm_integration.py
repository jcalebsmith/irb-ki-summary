"""
Generic Azure OpenAI Integration with Structured Outputs
Provides base LLM functionality with Pydantic model support
"""
import os
import json
from typing import Dict, Any, List, Optional, Union, Type
from dotenv import load_dotenv
from pathlib import Path
from pydantic import BaseModel
from llama_index.llms.azure_openai import AzureOpenAI as AzureOpenAILLM
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.core.llms import ChatMessage
from llama_index.core.prompts import PromptTemplate
from app.core.exceptions import LLMError, ExtractionError

# Load environment variables from app/.env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class GenericLLMExtractor:
    """
    Generic Azure OpenAI client for document extraction
    """
    
    def __init__(self):
        """Initialize Azure OpenAI client using LlamaIndex with structured output support"""
        organization = os.getenv("ORGANIZATION", "231173")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        # Use latest API version for structured outputs
        api_version = os.getenv("API_VERSION", "2024-10-21")
        
        # Use LlamaIndex Azure OpenAI client with structured output support
        self.llm = AzureOpenAILLM(
            model="gpt-4o",
            engine="gpt-4o",
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_LLM", "text-embedding-3-small"),
            api_key=api_key,
            azure_endpoint=azure_endpoint,
            api_version=api_version,
            default_headers={"OpenAI-Organization": organization, "Shortcode": organization},
            temperature=0,  # Minimum temperature for consistency
            top_p=0.0,      # Deterministic sampling
            organization=organization,
        )
        
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
        try:
            # Build system prompt
            if not system_prompt:
                system_prompt = (
                    "You are an expert at extracting structured information from documents. "
                    "Extract the requested information accurately and concisely. "
                    "Follow the schema requirements strictly."
                )
            
            # Convert LLM to structured LLM with Pydantic model
            structured_llm = self.llm.as_structured_llm(output_cls=output_cls)
            
            # Build messages
            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=f"Extract information from this document:\n\n{document_context[:8000]}")
            ]
            
            # Get structured response
            response = structured_llm.chat(messages)
            
            # The response.raw contains the Pydantic model instance
            result = response.raw
            
            return result
            
        except Exception as e:
            raise LLMError(
                "structured_extraction",
                f"Failed to extract structured data: {str(e)}",
                {"output_class": output_cls.__name__}
            )
    
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
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_prompt)
            ]
            
            # Use LlamaIndex LLM for chat completion
            response = self.llm.chat(messages)
            
            # Parse response
            response_text = response.message.content
            # Try to extract JSON from the response
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to find JSON in the response
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
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
                ChatMessage(
                    role="system",
                    content=f"Extract the requested information in {max_words} words or less."
                ),
                ChatMessage(
                    role="user",
                    content=f"{query}\n\nDocument:\n{document_context[:4000]}"
                )
            ]
            
            # Use LlamaIndex LLM for chat completion
            response = self.llm.chat(messages)
            
            result = response.message.content.strip()
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
            
            # Use LlamaIndex LLM for chat completion
            response = self.llm.chat(messages)
            
            answer = response.message.content.strip().upper()
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
                ChatMessage(
                    role="system",
                    content=(
                        f"Based on the document, select the most appropriate option from: "
                        f"{', '.join(allowed_values)}. Return only the selected option."
                    )
                ),
                ChatMessage(
                    role="user",
                    content=f"{query}\n\nDocument:\n{document_context[:4000]}"
                )
            ]
            
            # Use LlamaIndex LLM for chat completion
            response = self.llm.chat(messages)
            
            result = response.message.content.strip()
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
                      temperature: float = 0.7) -> str:
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
                messages.append(ChatMessage(role="system", content=system_prompt))
            messages.append(ChatMessage(role="user", content=prompt))
            
            # Use LlamaIndex LLM for chat completion
            response = self.llm.chat(messages)
            
            return response.message.content
            
        except Exception as e:
            raise LLMError(
                "completion",
                f"Failed to generate completion: {str(e)}",
                {"prompt_length": len(prompt), "temperature": temperature}
            )
    


# Global instance
_extractor_instance = None

def get_generic_extractor() -> GenericLLMExtractor:
    """Get or create global generic extractor instance"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = GenericLLMExtractor()
    return _extractor_instance

# Backward compatibility alias
def get_extractor():
    """Backward compatibility - returns generic extractor"""
    return get_generic_extractor()