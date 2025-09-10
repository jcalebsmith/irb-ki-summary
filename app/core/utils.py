"""
Common utilities for the document generation framework.

This module consolidates reusable functions to eliminate code duplication
across the codebase.
"""

import re
import hashlib
from pathlib import Path
from typing import Optional, Any, Union
import json
import numpy as np
from datetime import datetime


class TextProcessingUtils:
    """Utilities for text processing and manipulation."""
    
    @staticmethod
    def limit_words(text: str, max_words: int) -> str:
        """
        Limit text to a maximum number of words.
        
        Args:
            text: The text to limit
            max_words: Maximum number of words
            
        Returns:
            Text limited to max_words
        """
        words = text.split()
        if len(words) <= max_words:
            return text
        return ' '.join(words[:max_words])
    
    @staticmethod
    def remove_duplicates(items: list[str]) -> list[str]:
        """
        Remove duplicate items while preserving order.
        
        Args:
            items: List of items possibly containing duplicates
            
        Returns:
            List with duplicates removed
        """
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result
    
    @staticmethod
    def capitalize_first(text: str) -> str:
        """
        Capitalize the first letter of text.
        
        Args:
            text: Text to capitalize
            
        Returns:
            Text with first letter capitalized
        """
        if not text:
            return text
        return text[0].upper() + text[1:] if len(text) > 1 else text.upper()
    
    @staticmethod
    def extract_sentences(text: str) -> list[str]:
        """
        Extract sentences from text.
        
        Args:
            text: Text to extract sentences from
            
        Returns:
            List of sentences
        """
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    @staticmethod
    def count_words(text: str) -> int:
        """
        Count words in text.
        
        Args:
            text: Text to count words in
            
        Returns:
            Number of words
        """
        return len(text.split())
    
    @staticmethod
    def clean_whitespace(text: str) -> str:
        """
        Clean excessive whitespace from text.
        
        Args:
            text: Text to clean
            
        Returns:
            Text with normalized whitespace
        """
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        return text.strip()


class PathUtils:
    """Utilities for file path handling."""
    
    @staticmethod
    def resolve_template_path(template_dir: Path, 
                            document_type: str,
                            template_name: str) -> Optional[Path]:
        """
        Resolve template path with consistent logic.
        
        Args:
            template_dir: Base template directory
            document_type: Type of document
            template_name: Name of template file
            
        Returns:
            Resolved template path or None if not found
        """
        # Try document-specific path first
        template_path = template_dir / document_type / template_name
        if template_path.exists():
            return template_path
        
        # Try base templates
        template_path = template_dir / "base" / template_name
        if template_path.exists():
            return template_path
        
        # Try without document type directory
        template_path = template_dir / template_name
        if template_path.exists():
            return template_path
        
        return None
    
    @staticmethod
    def ensure_directory(path: Union[str, Path]) -> Path:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            path: Directory path
            
        Returns:
            Path object for the directory
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def get_file_extension(path: Union[str, Path]) -> str:
        """
        Get file extension without the dot.
        
        Args:
            path: File path
            
        Returns:
            File extension
        """
        return Path(path).suffix.lstrip('.')
    
    @staticmethod
    def is_valid_file(path: Union[str, Path], 
                     extensions: Optional[list[str]] = None) -> bool:
        """
        Check if a path points to a valid file.
        
        Args:
            path: File path to check
            extensions: Optional list of valid extensions
            
        Returns:
            True if file exists and has valid extension
        """
        path = Path(path)
        if not path.exists() or not path.is_file():
            return False
        
        if extensions:
            ext = path.suffix.lstrip('.')
            return ext.lower() in [e.lower() for e in extensions]
        
        return True


class HashUtils:
    """Utilities for hashing and content fingerprinting."""
    
    @staticmethod
    def content_hash(content: str, algorithm: str = "md5") -> str:
        """
        Generate hash of content.
        
        Args:
            content: Content to hash
            algorithm: Hash algorithm (md5, sha256)
            
        Returns:
            Hex digest of hash
        """
        if algorithm == "md5":
            hasher = hashlib.md5()
        elif algorithm == "sha256":
            hasher = hashlib.sha256()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        hasher.update(content.encode('utf-8'))
        return hasher.hexdigest()
    
    @staticmethod
    def short_hash(content: str, length: int = 8) -> str:
        """
        Generate a short hash for identification.
        
        Args:
            content: Content to hash
            length: Length of hash to return
            
        Returns:
            Short hash string
        """
        full_hash = HashUtils.content_hash(content, "md5")
        return full_hash[:length]
    
    @staticmethod
    def file_hash(file_path: Union[str, Path], 
                 algorithm: str = "sha256") -> str:
        """
        Generate hash of file contents.
        
        Args:
            file_path: Path to file
            algorithm: Hash algorithm
            
        Returns:
            Hex digest of file hash
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if algorithm == "md5":
            hasher = hashlib.md5()
        elif algorithm == "sha256":
            hasher = hashlib.sha256()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        
        return hasher.hexdigest()


class MetricsUtils:
    """Utilities for calculating metrics and statistics."""
    
    @staticmethod
    def coefficient_of_variation(values: list[float]) -> float:
        """
        Calculate coefficient of variation.
        
        Args:
            values: List of numeric values
            
        Returns:
            CV as percentage
        """
        if len(values) < 2:
            return 0.0
        
        mean = np.mean(values)
        if mean == 0:
            return 0.0
        
        std = np.std(values)
        return (std / mean) * 100
    
    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts using Jaccard index.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        # Convert to word sets
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Calculate Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    @staticmethod
    def calculate_stats(values: list[float]) -> dict[str, float]:
        """
        Calculate basic statistics for a list of values.
        
        Args:
            values: List of numeric values
            
        Returns:
            Dictionary with mean, std, min, max, cv
        """
        if not values:
            return {
                "mean": 0.0,
                "std": 0.0,
                "min": 0.0,
                "max": 0.0,
                "cv": 0.0
            }
        
        return {
            "mean": np.mean(values),
            "std": np.std(values),
            "min": np.min(values),
            "max": np.max(values),
            "cv": MetricsUtils.coefficient_of_variation(values)
        }


class JSONUtils:
    """Utilities for JSON handling."""
    
    @staticmethod
    def safe_parse(json_str: str, default: Any = None) -> Any:
        """
        Safely parse JSON string.
        
        Args:
            json_str: JSON string to parse
            default: Default value if parsing fails
            
        Returns:
            Parsed JSON or default value
        """
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return default
    
    @staticmethod
    def extract_json_from_text(text: str) -> Optional[dict]:
        """
        Extract JSON object from text that may contain other content.
        
        Args:
            text: Text possibly containing JSON
            
        Returns:
            Extracted JSON dict or None
        """
        # Try to find JSON object in text
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return JSONUtils.safe_parse(match.group(0))
        return None
    
    @staticmethod
    def serialize_with_types(obj: Any) -> Any:
        """
        Serialize object handling special types.
        
        Args:
            obj: Object to serialize
            
        Returns:
            JSON-serializable object
        """
        if isinstance(obj, (datetime, Path)):
            return str(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return obj


class ValidationUtils:
    """Utilities for validation operations."""
    
    @staticmethod
    def is_email(text: str) -> bool:
        """
        Check if text is a valid email address.
        
        Args:
            text: Text to check
            
        Returns:
            True if valid email
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, text))
    
    @staticmethod
    def is_url(text: str) -> bool:
        """
        Check if text is a valid URL.
        
        Args:
            text: Text to check
            
        Returns:
            True if valid URL
        """
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, text, re.IGNORECASE))
    
    @staticmethod
    def is_phone(text: str) -> bool:
        """
        Check if text is a valid phone number.
        
        Args:
            text: Text to check
            
        Returns:
            True if valid phone number
        """
        # Remove common separators
        cleaned = re.sub(r'[\s\-\(\)]+', '', text)
        # Check if it's a valid phone pattern
        pattern = r'^\+?1?\d{10,14}$'
        return bool(re.match(pattern, cleaned))
    
    @staticmethod
    def validate_required_fields(data: dict[str, Any], 
                                required: list[str]) -> tuple[bool, list[str]]:
        """
        Validate that required fields are present.
        
        Args:
            data: Data dictionary to validate
            required: List of required field names
            
        Returns:
            Tuple of (is_valid, list_of_missing_fields)
        """
        missing = []
        for field in required:
            if field not in data or not data[field]:
                missing.append(field)
        
        return len(missing) == 0, missing


class TemplateUtils:
    """Utilities for template operations."""
    
    @staticmethod
    def extract_variables(template: str) -> list[str]:
        """
        Extract variable names from a template string.
        
        Args:
            template: Template string with {{variables}}
            
        Returns:
            List of variable names
        """
        pattern = r'\{\{\s*(\w+)\s*\}\}'
        matches = re.findall(pattern, template)
        return list(set(matches))
    
    @staticmethod
    def simple_render(template: str, context: dict[str, Any]) -> str:
        """
        Simple template rendering without Jinja2.
        
        Args:
            template: Template string
            context: Context dictionary
            
        Returns:
            Rendered template
        """
        result = template
        for key, value in context.items():
            pattern = r'\{\{\s*' + re.escape(key) + r'\s*\}\}'
            result = re.sub(pattern, str(value), result)
        return result
    
    @staticmethod
    def has_unfilled_variables(text: str) -> bool:
        """
        Check if text has unfilled template variables.
        
        Args:
            text: Text to check
            
        Returns:
            True if unfilled variables exist
        """
        pattern = r'\{\{\s*\w+\s*\}\}'
        return bool(re.search(pattern, text))