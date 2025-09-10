"""
Test utilities for the document generation framework.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Tuple, Any, Optional
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / 'app' / '.env'
load_dotenv(env_path)


def setup_azure_openai() -> Tuple[Any, Any]:
    """
    Set up Azure OpenAI embedding model and LLM for testing.
    
    Returns:
        Tuple of (embed_model, llm)
    """
    from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
    from llama_index.llms.azure_openai import AzureOpenAI as AzureOpenAILLM
    
    organization = os.getenv("ORGANIZATION", "231173")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("API_VERSION", "2024-10-21")
    
    # Initialize embedding model
    embed_model = AzureOpenAIEmbedding(
        model="text-embedding-3-small",
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_EMBEDDING", "text-embedding-3-small"),
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        api_version=api_version,
        default_headers={"OpenAI-Organization": organization, "Shortcode": organization}
    )
    
    # Initialize LLM
    llm = AzureOpenAILLM(
        model="gpt-4o",
        engine="gpt-4o",
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_LLM", "gpt-4o"),
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        api_version=api_version,
        default_headers={"OpenAI-Organization": organization, "Shortcode": organization},
        temperature=0,
        top_p=0.0,
        organization=organization
    )
    
    return embed_model, llm


def calculate_content_hash(content: str) -> str:
    """
    Calculate SHA256 hash of content for consistency checking.
    
    Args:
        content: String content to hash
        
    Returns:
        Hex digest of SHA256 hash
    """
    return hashlib.sha256(content.encode()).hexdigest()


def save_test_results(results: dict, filename: str) -> None:
    """
    Save test results to a JSON file.
    
    Args:
        results: Dictionary of test results
        filename: Output filename
    """
    output_path = Path(filename)
    
    # Convert any non-serializable objects
    def convert_types(obj):
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        elif isinstance(obj, Path):
            return str(obj)
        return obj
    
    # Recursively convert the results
    serializable_results = json.loads(
        json.dumps(results, default=convert_types)
    )
    
    with open(output_path, 'w') as f:
        json.dump(serializable_results, f, indent=2)
    
    print(f"Test results saved to {output_path}")


def convert_numpy_types(obj: Any) -> Any:
    """
    Convert numpy types to Python native types for JSON serialization.
    
    Args:
        obj: Object to convert
        
    Returns:
        Converted object
    """
    import numpy as np
    
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj