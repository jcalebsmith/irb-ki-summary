"""
Simplified Plugin Base Class for Document Generation
Reduces complexity while maintaining extensibility
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PluginConfig:
    """Simplified plugin configuration"""
    name: str
    version: str
    supported_types: List[str]
    template_dir: str
    extraction_schema: Dict[str, Any]
    critical_fields: List[str] = None
    
    def __post_init__(self):
        if self.critical_fields is None:
            self.critical_fields = []


class SimpleDocumentPlugin(ABC):
    """
    Simplified plugin base class with only essential methods.
    Reduces from 7 abstract methods to 3.
    """
    
    def __init__(self):
        self.config = self.get_config()
    
    @abstractmethod
    def get_config(self) -> PluginConfig:
        """Return plugin configuration"""
        pass
    
    @abstractmethod
    async def extract(self, document: str, llm_client: Any = None) -> Dict[str, Any]:
        """
        Extract structured data from document.
        
        Args:
            document: Document text to extract from
            llm_client: Optional LLM client for extraction
            
        Returns:
            Dictionary of extracted values
        """
        pass
    
    @abstractmethod  
    def get_template_path(self, template_name: str = "main") -> str:
        """
        Get path to template file.
        
        Args:
            template_name: Name of template (default: "main")
            
        Returns:
            Path to template file
        """
        pass
    
    def supports(self, doc_type: str) -> bool:
        """Check if plugin supports document type"""
        return doc_type.lower() in [t.lower() for t in self.config.supported_types]
    
    def get_validation_rules(self) -> Dict[str, Any]:
        """Return validation rules derived from extraction schema"""
        rules = {
            "required_fields": [],
            "max_lengths": {},
            "allowed_values": {}
        }
        
        # Auto-generate rules from extraction schema
        for field, spec in self.config.extraction_schema.items():
            if spec.get("required", False):
                rules["required_fields"].append(field)
            
            if "max_words" in spec:
                # Convert word limit to character limit (approx 5 chars per word)
                rules["max_lengths"][field] = spec["max_words"] * 5
            
            if spec.get("type") == "enum" and "options" in spec:
                rules["allowed_values"][field] = spec["options"]
        
        return rules
    
    def get_info(self) -> Dict[str, Any]:
        """Return plugin information"""
        return {
            "name": self.config.name,
            "version": self.config.version, 
            "supported_types": self.config.supported_types,
            "critical_fields": self.config.critical_fields
        }