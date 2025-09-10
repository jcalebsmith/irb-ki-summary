"""
Enhanced RAG Pipeline with SPLICE Chunking Method
Implements Semantic Preservation with Length-Informed Chunking Enhancement
"""
from typing import List, Dict, Any, Optional, Tuple, Generator
from dataclasses import dataclass, field
import re
from collections import deque
import numpy as np
from llama_index.core.node_parser import NodeParser, SimpleNodeParser
from llama_index.core.schema import BaseNode, TextNode, Document
from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import LLMRerank


@dataclass
class ChunkMetadata:
    """Metadata for a chunk with hierarchical information"""
    chunk_id: str
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    section_type: Optional[str] = None
    semantic_group: Optional[int] = None
    boundary_type: str = "soft"  # soft, hard, semantic
    overlap_tokens: int = 0
    hierarchical_level: int = 0


class SPLICEChunker:
    """
    SPLICE: Semantic Preservation with Length-Informed Chunking Enhancement
    Implements structure-aware chunking with semantic boundaries
    """
    
    def __init__(self,
                 min_chunk_size: int = 128,
                 target_chunk_size: int = 256,
                 max_chunk_size: int = 512,
                 overlap_ratio: float = 0.1,
                 semantic_threshold: float = 0.7):
        """
        Initialize SPLICE chunker
        
        Args:
            min_chunk_size: Minimum tokens per chunk
            target_chunk_size: Target tokens per chunk
            max_chunk_size: Maximum tokens per chunk
            overlap_ratio: Overlap between chunks as ratio of chunk size
            semantic_threshold: Threshold for semantic similarity grouping
        """
        self.min_chunk_size = min_chunk_size
        self.target_chunk_size = target_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_ratio = overlap_ratio
        self.semantic_threshold = semantic_threshold
        
        # Structural markers for different document types
        self.structure_markers = {
            'section': r'^(?:Section|SECTION|Part|PART)\s+\d+',
            'subsection': r'^(?:\d+\.\d+|\([a-z]\)|\w\))',
            'list_item': r'^(?:[-•*]|\d+[.)]\s)',
            'paragraph_break': r'\n\n+',
            'sentence_end': r'[.!?]\s+',
            'header': r'^(?:[A-Z][A-Z\s]{2,}:?|#{1,6}\s+)',
        }
    
    def identify_boundaries(self, text: str) -> List[Tuple[int, str]]:
        """
        Identify structural boundaries in text
        
        Returns:
            List of (position, boundary_type) tuples
        """
        boundaries = []
        
        for boundary_type, pattern in self.structure_markers.items():
            for match in re.finditer(pattern, text, re.MULTILINE):
                boundaries.append((match.start(), boundary_type))
        
        # Sort by position
        boundaries.sort(key=lambda x: x[0])
        return boundaries
    
    def calculate_semantic_groups(self, chunks: List[str]) -> List[int]:
        """
        Group chunks by semantic similarity
        Simple implementation - in production would use embeddings
        """
        # For now, use simple keyword overlap as proxy for semantic similarity
        groups = []
        current_group = 0
        
        for i, chunk in enumerate(chunks):
            if i == 0:
                groups.append(current_group)
                continue
            
            # Calculate simple similarity with previous chunk
            prev_words = set(chunks[i-1].lower().split())
            curr_words = set(chunk.lower().split())
            
            if not prev_words:
                similarity = 0
            else:
                similarity = len(prev_words & curr_words) / len(prev_words | curr_words)
            
            if similarity < self.semantic_threshold:
                current_group += 1
            
            groups.append(current_group)
        
        return groups
    
    def apply_overlap_policy(self, chunks: List[str], boundaries: List[Tuple[int, str]]) -> List[str]:
        """
        Apply intelligent overlap based on boundary types and semantic similarity
        """
        enhanced_chunks = []
        
        for i, chunk in enumerate(chunks):
            if i == 0:
                enhanced_chunks.append(chunk)
                continue
            
            # Determine overlap size based on boundary type
            overlap_tokens = int(len(chunk.split()) * self.overlap_ratio)
            
            # Get tokens from previous chunk for overlap
            prev_tokens = chunks[i-1].split()
            
            if overlap_tokens > 0 and len(prev_tokens) >= overlap_tokens:
                overlap_text = ' '.join(prev_tokens[-overlap_tokens:])
                enhanced_chunk = overlap_text + ' ' + chunk
            else:
                enhanced_chunk = chunk
            
            enhanced_chunks.append(enhanced_chunk)
        
        return enhanced_chunks
    
    def chunk_document(self, text: str) -> List[Tuple[str, ChunkMetadata]]:
        """
        Chunk document using SPLICE method
        
        Returns:
            List of (chunk_text, metadata) tuples
        """
        # Identify structural boundaries
        boundaries = self.identify_boundaries(text)
        
        # Create initial chunks respecting boundaries
        chunks = []
        current_chunk = []
        current_tokens = 0
        current_pos = 0
        chunk_boundaries = []
        
        tokens = text.split()
        
        for token_idx, token in enumerate(tokens):
            current_chunk.append(token)
            current_tokens += 1
            
            # Check if we're at a boundary
            token_pos = len(' '.join(tokens[:token_idx+1]))
            boundary_type = None
            for bound_pos, bound_type in boundaries:
                if abs(token_pos - bound_pos) < 10:  # Within 10 chars of boundary
                    boundary_type = bound_type
                    break
            
            # Decide whether to create a chunk
            should_chunk = False
            
            if boundary_type in ['section', 'subsection', 'header']:
                # Hard boundary - always chunk unless too small
                if current_tokens >= self.min_chunk_size:
                    should_chunk = True
            elif current_tokens >= self.target_chunk_size:
                # Reached target size - look for soft boundary
                if boundary_type in ['paragraph_break', 'sentence_end']:
                    should_chunk = True
                elif current_tokens >= self.max_chunk_size:
                    # Force chunk at max size
                    should_chunk = True
            
            if should_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)
                chunk_boundaries.append(boundary_type or 'soft')
                current_chunk = []
                current_tokens = 0
        
        # Add remaining text as final chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            chunk_boundaries.append('soft')
        
        # Calculate semantic groups
        semantic_groups = self.calculate_semantic_groups(chunks)
        
        # Apply overlap policy
        enhanced_chunks = self.apply_overlap_policy(chunks, boundaries)
        
        # Create metadata for each chunk
        result = []
        for i, chunk in enumerate(enhanced_chunks):
            metadata = ChunkMetadata(
                chunk_id=f"chunk_{i}",
                parent_id=f"chunk_{i-1}" if i > 0 else None,
                children_ids=[f"chunk_{i+1}"] if i < len(enhanced_chunks) - 1 else [],
                semantic_group=semantic_groups[i] if i < len(semantic_groups) else 0,
                boundary_type=chunk_boundaries[i] if i < len(chunk_boundaries) else 'soft',
                overlap_tokens=int(len(chunk.split()) * self.overlap_ratio) if i > 0 else 0,
                hierarchical_level=0  # Would be set based on document structure
            )
            result.append((chunk, metadata))
        
        return result


class StreamingRAGPipeline:
    """
    Enhanced RAG pipeline with streaming capabilities and SPLICE chunking
    """
    
    def __init__(self, 
                 chunking_method: str = "SPLICE",
                 embed_model: Any = None,
                 llm: Any = None):
        """
        Initialize streaming RAG pipeline
        
        Args:
            chunking_method: Chunking method to use (SPLICE or traditional)
            embed_model: Embedding model for vector store
            llm: Language model for generation
        """
        self.chunking_method = chunking_method
        self.embed_model = embed_model
        self.llm = llm
        
        if chunking_method == "SPLICE":
            self.chunker = SPLICEChunker()
        else:
            self.chunker = SimpleNodeParser(
                chunk_size=256,
                chunk_overlap=20
            )
        
        self.vector_store_index: Optional[VectorStoreIndex] = None
        self.query_engine: Optional[RetrieverQueryEngine] = None
        
        self.chunk_metadata_store: Dict[str, ChunkMetadata] = {}
    
    def process_document(self, document: Document) -> List[BaseNode]:
        """
        Process document into chunks using selected method
        """
        if self.chunking_method == "SPLICE":
            # Use SPLICE chunking
            chunks_with_metadata = self.chunker.chunk_document(document.text)
            
            nodes = []
            for chunk_text, metadata in chunks_with_metadata:
                node = TextNode(
                    text=chunk_text,
                    metadata={
                        "chunk_id": metadata.chunk_id,
                        "parent_id": metadata.parent_id,
                        "semantic_group": metadata.semantic_group,
                        "boundary_type": metadata.boundary_type,
                        "hierarchical_level": metadata.hierarchical_level
                    }
                )
                nodes.append(node)
                # Store metadata for later use
                self.chunk_metadata_store[metadata.chunk_id] = metadata
            
            return nodes
        else:
            # Use traditional chunking
            return self.chunker.get_nodes_from_documents([document])
    
    def build_index(self, nodes: List[BaseNode]):
        """Build vector store index from nodes"""
        self.vector_store_index = VectorStoreIndex(
            nodes,
            embed_model=self.embed_model
        )
        
        # Set up retriever with reranking
        retriever = VectorIndexRetriever(
            index=self.vector_store_index,
            similarity_top_k=8
        )
        
        # Configure query engine with LLM reranking
        rerank_postprocessor = LLMRerank(
            llm=self.llm,
            top_n=4
        )
        
        self.query_engine = RetrieverQueryEngine(
            retriever=retriever,
            node_postprocessors=[rerank_postprocessor]
        )
    
    def stream_query(self, query: str) -> Generator[str, None, None]:
        """
        Stream query results progressively
        
        Yields:
            Chunks of generated text as they become available
        """
        if not self.query_engine:
            yield "Error: Index not built. Process documents first."
            return
        
        # Get initial retrieval results
        response = self.query_engine.query(query)
        
        # Stream the response in chunks
        text = str(response)
        words = text.split()
        
        # Stream words in small batches for progressive rendering
        batch_size = 5
        for i in range(0, len(words), batch_size):
            batch = words[i:i + batch_size]
            yield ' '.join(batch) + ' '
    
    def get_hierarchical_context(self, chunk_id: str) -> Dict[str, Any]:
        """
        Get hierarchical context for a chunk including parents and siblings
        """
        if chunk_id not in self.chunk_metadata_store:
            return {}
        
        metadata = self.chunk_metadata_store[chunk_id]
        context = {
            "current": chunk_id,
            "parent": metadata.parent_id,
            "children": metadata.children_ids,
            "semantic_group": metadata.semantic_group,
            "siblings": []
        }
        
        # Find siblings (same semantic group)
        for other_id, other_metadata in self.chunk_metadata_store.items():
            if (other_id != chunk_id and 
                other_metadata.semantic_group == metadata.semantic_group):
                context["siblings"].append(other_id)
        
        return context
    
