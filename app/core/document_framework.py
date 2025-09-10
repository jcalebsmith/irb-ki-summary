"""
Document Generation Framework
Main orchestrator that combines plugin architecture, Jinja2 templates, and RAG pipeline
"""
from typing import Dict, Any, List, Optional, Tuple, Union
import asyncio
from pathlib import Path
from dataclasses import dataclass, field
import re
import hashlib
from collections import defaultdict
import numpy as np
import sys
sys.path.append(str(Path(__file__).parent.parent))
from logger import get_logger

from .plugin_manager import PluginManager, ValidationRuleSet
from .template_engine import Jinja2Engine
from .rag_pipeline import StreamingRAGPipeline
from .multi_agent_system import MultiAgentPool
from .validators import ValidationOrchestrator, EnhancedValidationOrchestrator
from .exceptions import (
    DocumentFrameworkError,
    PluginNotFoundError,
    TemplateError,
    ValidationError,
    RAGPipelineError
)
from .types import (
    ValidationResult, ValidationConstants, ProcessingConstants,
    DocumentMetadata, SectionContent, ErrorCodes, ProcessingError
)
from llama_index.core.schema import Document

# Set up module logger
logger = get_logger("core.document_framework")


@dataclass
class GenerationResult:
    """Result of document generation"""
    success: bool
    content: str
    metadata: Dict[str, Any]
    validation_results: Dict[str, Any]
    error_message: Optional[str] = None


# ConsistencyMetrics has been moved to validators.py as part of the refactoring
# Import it from there for backward compatibility
from .validators import ConsistencyMetrics


# EnhancedValidationOrchestrator has been refactored into smaller, focused validators
# The class is now imported from validators.py where it has been redesigned
# with modular components (FieldValidator, ContentQualityValidator, etc.)
# The original monolithic class is preserved there as ValidationOrchestrator
# with an alias for backward compatibility

# The EnhancedValidationOrchestrator has been refactored into smaller components
# and moved to validators.py for better separation of concerns.
# All validation logic is now modular with focused validator classes:
# - FieldValidator: handles field-level validation
# - ContentQualityValidator: checks content quality and prohibited phrases  
# - StructuralValidator: validates document structure
# - CriticalValueValidator: ensures critical values are preserved
# - ValidationOrchestrator: coordinates all validators
# The original class is preserved in validators.py for backward compatibility


# Import the refactored validation classes for backward compatibility
# EnhancedValidationOrchestrator is now an alias in validators.py
from .validators import EnhancedValidationOrchestrator, ValidationOrchestrator


class DocumentGenerationFramework:
    """
    Main framework for document generation with plugin architecture
    """
    
    def __init__(self, 
                 plugin_dir: str = "app/plugins",
                 template_dir: str = "app/templates",
                 embed_model: Any = None,
                 llm: Any = None):
        """
        Initialize document generation framework
        
        Args:
            plugin_dir: Directory containing document plugins
            template_dir: Directory containing Jinja2 templates
            embed_model: Embedding model for RAG pipeline
            llm: Language model for generation
        """
        self.plugin_manager = PluginManager(plugin_dir)
        self.template_engine = Jinja2Engine(template_dir)
        self.rag_pipeline = StreamingRAGPipeline(
            chunking_method="SPLICE",
            embed_model=embed_model,
            llm=llm
        )
        self.validation_orchestrator = ValidationOrchestrator()
        self.agent_pool = MultiAgentPool(llm=llm)  # Pass LLM to multi-agent system
    
    def get_global_parameters(self) -> Dict[str, Any]:
        """Get global parameters for template rendering"""
        return {
            "framework_version": "1.0.0",
            "generation_timestamp": str(Path.cwd()),
            "available_plugins": self.plugin_manager.list_plugins()
        }
    
    async def generate(self, 
                      document_type: str, 
                      parameters: Dict[str, Any],
                      document: Optional[Document] = None) -> GenerationResult:
        """
        Generate document using plugin-based architecture.
        
        This method orchestrates the entire document generation pipeline:
        1. Plugin selection
        2. Document processing (if provided)
        3. Agent orchestration
        4. Template rendering
        5. Validation
        
        Args:
            document_type: Type of document to generate
            parameters: Parameters for document generation
            document: Optional source document for extraction
            
        Returns:
            GenerationResult with generated content and metadata
        """
        try:
            # Step 1: Select and validate plugin
            plugin = await self._select_plugin(document_type)
            if not plugin:
                return self._create_error_result(
                    f"No plugin found for document type: {document_type}"
                )
            
            # Step 2: Build context from document and parameters
            context = await self._build_context(parameters, document)
            
            # Store parameters for workflow tracking
            self._last_parameters = parameters
            
            # Step 3: Resolve template
            template_path = await self._resolve_template(plugin, parameters)
            if not template_path:
                return self._create_error_result("Failed to resolve template")
            
            # Step 4: Run agent orchestration
            agent_results = await self._run_agents(plugin, parameters)
            context = self._merge_agent_results(context, agent_results)
            
            # Step 5: Render template
            rendered_content = await self._render_template(
                template_path, context
            )
            
            # Step 6: Validate results
            validation_results = await self._validate_output(
                plugin, context, rendered_content
            )
            
            # Step 7: Create final result
            return self._create_generation_result(
                plugin, template_path, document_type,
                rendered_content, validation_results
            )
            
        except DocumentFrameworkError:
            # Re-raise framework errors as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise DocumentFrameworkError(
                f"Document generation failed: {str(e)}",
                {"document_type": document_type}
            )
    
    async def _select_plugin(self, document_type: str):
        """Select the appropriate plugin for the document type."""
        return self.plugin_manager.get_plugin(document_type)
    
    async def _build_context(self, parameters: Dict[str, Any], 
                            document: Optional[Document]) -> Dict[str, Any]:
        """Build context from parameters and optional document.
        
        If a document is provided, it will be processed using the RAG pipeline
        to extract relevant information.
        """
        context = parameters.copy()
        
        if document:
            # Process document using SPLICE chunking for optimal retrieval
            nodes = self.rag_pipeline.process_document(document)
            self.rag_pipeline.build_index(nodes)
            context["document_processed"] = True
            
        return context
    
    async def _resolve_template(self, plugin: Any, parameters: dict[str, Any]) -> Optional[str]:
        """Resolve the template path based on plugin and parameters."""
        return plugin.resolve_template(parameters)
    
    async def _run_agents(self, plugin: Any, parameters: dict[str, Any]) -> dict[str, Any]:
        """Run multi-agent orchestration for document processing."""
        agents = plugin.get_specialized_agents()
        return await self.agent_pool.orchestrate(agents, parameters)
    
    def _merge_agent_results(self, context: dict[str, Any], 
                           agent_results) -> Dict[str, Any]:
        """Merge agent results into the context.
        
        Handles both dictionary results and AgentContext objects.
        """
        if isinstance(agent_results, dict):
            context.update(agent_results)
        else:
            # Extract values from AgentContext object
            context.update({
                "extracted_values": getattr(agent_results, 'extracted_values', {}),
                "generated_content": getattr(agent_results, 'generated_content', {}),
                "validation_results": getattr(agent_results, 'validation_results', {})
            })
        return context
    
    async def _render_template(self, template_path: str, 
                              context: Dict[str, Any]) -> str:
        """Render the template with the provided context."""
        return self.template_engine.render(
            template_path=template_path,
            context=context,
            globals=self.get_global_parameters()
        )
    
    async def _validate_output(self, plugin, context: Dict[str, Any], 
                              rendered: str) -> Dict[str, Any]:
        """Validate the rendered output against plugin rules."""
        validation_rules = plugin.get_validation_rules()
        critical_values = plugin.get_critical_values()
        
        result = self.validation_orchestrator.validate(
            original=context,
            rendered=rendered,
            rules=validation_rules,
            critical_values=critical_values
        )
        
        # Debug logging
        print(f"DEBUG: Validation result - passed: {result.get('passed', 'N/A')}")
        if result.get('issues'):
            print(f"DEBUG: Validation issues: {result['issues'][:3]}")
        
        return result
    
    def _create_generation_result(self, plugin, template_path: str,
                                 document_type: str, content: str,
                                 validation_results: Dict[str, Any]) -> GenerationResult:
        """Create the final GenerationResult with metadata."""
        metadata = {
            "plugin_id": plugin.get_plugin_info().get("id"),
            "template_used": template_path,
            "document_type": document_type,
            "chunking_method": "SPLICE",
            "agents_used": len(plugin.get_specialized_agents())
        }
        
        # Add workflow tracking if plugin supports it
        if hasattr(plugin, 'process_workflow'):
            # Get parameters from the last generation context
            parameters = getattr(self, '_last_parameters', {})
            workflow_steps = plugin.process_workflow(parameters, content)
            metadata["workflow_steps"] = workflow_steps
        
        return GenerationResult(
            success=validation_results["passed"],
            content=content,
            metadata=metadata,
            validation_results=validation_results
        )
    
    def _create_error_result(self, error_message: str) -> GenerationResult:
        """Create an error GenerationResult."""
        return GenerationResult(
            success=False,
            content="",
            metadata={},
            validation_results={},
            error_message=error_message
        )
    
    def list_supported_document_types(self) -> List[str]:
        """List all supported document types"""
        return self.plugin_manager.get_supported_document_types()
    
    def get_plugin_info(self, document_type: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific plugin"""
        plugin = self.plugin_manager.get_plugin(document_type)
        if plugin:
            return plugin.get_plugin_info()
        return None
    
    def reload_plugins(self):
        """Reload all plugins (useful for development)"""
        self.plugin_manager.reload_plugins()
    
    def clear_template_cache(self):
        """Clear template value cache - deprecated, no longer uses cache"""
        pass
    
    async def stream_generate(self, 
                             document_type: str,
                             parameters: Dict[str, Any],
                             document: Optional[Document] = None):
        """
        Stream document generation for real-time updates
        
        Yields:
            Chunks of generated content as they become available
        """
        # Get plugin
        plugin = self.plugin_manager.get_plugin(document_type)
        if not plugin:
            yield f"Error: No plugin found for {document_type}"
            return
        
        # Process document with streaming
        if document:
            nodes = self.rag_pipeline.process_document(document)
            self.rag_pipeline.build_index(nodes)
        
        # Stream template rendering
        template_path = plugin.resolve_template(parameters)
        
        # For streaming, we'll process in chunks
        # This is a simplified version - production would be more sophisticated
        agents = plugin.get_specialized_agents()
        
        # Process agents and stream results
        for i, agent in enumerate(agents):
            if hasattr(agent, 'process'):
                result = await agent.process(parameters)
                yield f"Processing agent {i+1}/{len(agents)}...\n"
                
        # Final rendering
        context = await self.agent_pool.orchestrate(agents, parameters)
        rendered = self.template_engine.render(
            template_path=template_path,
            context=context,
            globals=self.get_global_parameters()
        )
        
        # Stream the final result in chunks
        words = rendered.split()
        batch_size = 10
        for i in range(0, len(words), batch_size):
            batch = words[i:i + batch_size]
            yield ' '.join(batch) + ' '