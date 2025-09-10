"""
Simple document models to replace LlamaIndex dependencies
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class Document:
    """
    Simple document class to replace LlamaIndex Document.
    Contains text content and optional metadata.
    """
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    doc_id: Optional[str] = None
    
    def __str__(self) -> str:
        return self.text
    
    def __len__(self) -> int:
        return len(self.text)


@dataclass
class TextNode:
    """
    Simple text node for chunking operations.
    Replaces LlamaIndex TextNode.
    """
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    node_id: Optional[str] = None
    
    def __str__(self) -> str:
        return self.text