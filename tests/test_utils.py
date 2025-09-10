"""
Test utilities for the document generation framework.
"""

import os
import json
import hashlib
import logging
import sys
from pathlib import Path
from typing import Tuple, Any, Optional
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / 'app' / '.env'
load_dotenv(env_path)


def setup_test_logging(name: str = __name__) -> logging.Logger:
    """
    Set up consistent logging for tests.
    
    Args:
        name: Logger name (defaults to module name)
    
    Returns:
        Configured logger instance
    """
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    return logging.getLogger(name)


def setup_test_paths():
    """
    Set up Python path for test imports.
    
    Returns:
        Tuple of (ROOT_DIR, APP_DIR) paths
    """
    ROOT_DIR = Path(__file__).parent.parent
    APP_DIR = ROOT_DIR / "app"
    
    # Add to sys.path if not already present
    if str(APP_DIR) not in sys.path:
        sys.path.append(str(APP_DIR))
    if str(ROOT_DIR) not in sys.path:
        sys.path.append(str(ROOT_DIR))
    
    return ROOT_DIR, APP_DIR


def setup_azure_openai() -> Tuple[Any, Any]:
    """
    Set up Azure OpenAI embedding model and LLM for testing.
    
    Returns:
        Tuple of (embed_model, llm) - embed_model is None for now, llm is GenericLLMExtractor
    """
    print("DEBUG: setup_azure_openai() - Starting", flush=True)
    
    from app.core.llm_integration import GenericLLMExtractor
    print("DEBUG: setup_azure_openai() - GenericLLMExtractor imported", flush=True)
    
    # Initialize LLM extractor which now uses direct OpenAI SDK
    print("DEBUG: setup_azure_openai() - About to create GenericLLMExtractor instance", flush=True)
    llm = GenericLLMExtractor()
    print(f"DEBUG: setup_azure_openai() - GenericLLMExtractor created: {llm}", flush=True)
    
    # Embedding model not needed anymore since RAG pipeline was removed
    embed_model = None
    
    print("DEBUG: setup_azure_openai() - Returning", flush=True)
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