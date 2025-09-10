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


@dataclass
class ConsistencyMetrics:
    """Metrics for tracking generation consistency"""
    content_hashes: List[str] = field(default_factory=list)
    word_counts: List[int] = field(default_factory=list) 
    sentence_counts: List[int] = field(default_factory=list)
    critical_value_preservation_rate: float = 0.0
    structural_consistency_score: float = 0.0
    coefficient_of_variation: float = 0.0
    
    def calculate_coefficient_of_variation(self) -> float:
        """Calculate coefficient of variation for word counts.
        
        The CV is a measure of relative variability, calculated as the ratio
        of standard deviation to mean, expressed as a percentage.
        Lower CV values indicate more consistent document generation.
        Target: CV < 15% for good consistency.
        """
        if len(self.word_counts) < 2:
            return 0.0
        
        # Calculate mean (average) word count across all generations
        mean = np.mean(self.word_counts)
        
        # Calculate standard deviation (measure of spread)
        std = np.std(self.word_counts)
        
        # CV = (standard deviation / mean) * 100
        # Returns percentage showing relative variability
        return (std / mean * 100) if mean > 0 else 0.0
    
    def calculate_structural_consistency(self) -> float:
        """Calculate structural consistency based on content hashes"""
        if len(self.content_hashes) < 2:
            return 1.0
        unique_hashes = len(set(self.content_hashes))
        return 1.0 - (unique_hashes - 1) / len(self.content_hashes)


class EnhancedValidationOrchestrator:
    """Enhanced validation with strict consistency checking"""
    
    def __init__(self):
        self.validators = {}
        self.consistency_metrics = defaultdict(ConsistencyMetrics)
        # Use constants from types module for better maintainability
        self.prohibited_phrases = ValidationConstants.PROHIBITED_PHRASES
    
    def validate(self,
                 original: Dict[str, Any],
                 rendered: str,
                 rules: ValidationRuleSet,
                 critical_values: List[str],
                 document_type: str = "default") -> Dict[str, Any]:
        """
        Enhanced validation with consistency metrics
        
        Returns:
            Comprehensive validation results with consistency metrics
        """
        results = {
            "passed": True,
            "issues": [],
            "warnings": [],
            "info": [],
            "consistency_metrics": {},
            "content_analysis": {}
        }
        
        # Basic validation checks
        results = self._validate_required_fields(original, rules, results)
        results = self._validate_lengths(original, rendered, rules, results)
        results = self._validate_allowed_values(original, rules, results)
        
        # Enhanced consistency checks
        results = self._check_prohibited_phrases(rendered, results)
        results = self._validate_critical_values(original, rendered, critical_values, results)
        results = self._check_structural_consistency(rendered, results)
        results = self._check_sentence_quality(rendered, results)
        
        # Track consistency metrics
        self._track_consistency_metrics(rendered, document_type)
        
        # Add consistency thresholds check if provided in rules
        if hasattr(rules, 'consistency_thresholds'):
            results = self._check_consistency_thresholds(rules.consistency_thresholds, results)
        
        # Calculate overall consistency score
        results["consistency_metrics"] = self._calculate_consistency_score(document_type)
        
        return results
    
    def _validate_required_fields(self, original: Dict[str, Any], 
                                 rules: ValidationRuleSet, 
                                 results: Dict) -> Dict:
        """Validate required fields are present"""
        for field in rules.required_fields:
            if field not in original or not original[field]:
                results["issues"].append(f"Required field missing: {field}")
                results["passed"] = False
        return results
    
    def _validate_lengths(self, original: Dict[str, Any], 
                        rendered: str,
                        rules: ValidationRuleSet, 
                        results: Dict) -> Dict:
        """Validate field and section lengths"""
        # Check field lengths
        for field, max_length in rules.max_lengths.items():
            if field in original:
                field_length = len(str(original[field]))
                if field_length > max_length:
                    results["warnings"].append(
                        f"Field {field} exceeds max length: {field_length} > {max_length}"
                    )
        
        # Check overall document length
        word_count = len(rendered.split())
        results["content_analysis"]["word_count"] = word_count
        results["content_analysis"]["character_count"] = len(rendered)
        
        return results
    
    def _validate_allowed_values(self, original: Dict[str, Any],
                                rules: ValidationRuleSet,
                                results: Dict) -> Dict:
        """Validate fields contain allowed values"""
        # Debug check for proper type
        if not isinstance(original, dict):
            logger.error(f"_validate_allowed_values received non-dict type: {type(original)}")
            logger.error(f"Value is: {original}")
            # Convert to dict if possible
            if hasattr(original, '__dict__'):
                original = vars(original)
                logger.error(f"Converted to dict with keys: {original.keys()}")
            else:
                results["issues"].append(f"Cannot validate: original is {type(original)}, not dict")
                return results
                
        for field, allowed in rules.allowed_values.items():
            if field in original:
                value = original[field]
                if value not in allowed:
                    results["issues"].append(
                        f"Field {field} has invalid value: '{value}' not in {allowed}"
                    )
                    results["passed"] = False
        return results
    
    def _check_prohibited_phrases(self, rendered: str, results: Dict) -> Dict:
        """Check for prohibited phrases that indicate LLM artifacts"""
        found_phrases = []
        for phrase in self.prohibited_phrases:
            if phrase.lower() in rendered.lower():
                found_phrases.append(phrase)
        
        if found_phrases:
            results["issues"].append(f"Prohibited phrases found: {', '.join(found_phrases)}")
            results["passed"] = False
        
        return results
    
    def _validate_critical_values(self, original: Dict[str, Any],
                                 rendered: str,
                                 critical_values: List[str],
                                 results: Dict) -> Dict:
        """Validate critical values are preserved exactly"""
        preserved = 0
        total = 0
        
        for critical_field in critical_values:
            if critical_field in original:
                total += 1
                critical_value = str(original[critical_field])
                if critical_value in rendered:
                    preserved += 1
                else:
                    results["issues"].append(
                        f"Critical value '{critical_value}' for field '{critical_field}' not preserved"
                    )
                    results["passed"] = False
        
        if total > 0:
            preservation_rate = preserved / total
            results["content_analysis"]["critical_value_preservation"] = preservation_rate
            
            if preservation_rate < 1.0:
                results["warnings"].append(
                    f"Critical value preservation rate: {preservation_rate:.1%}"
                )
        
        return results
    
    def _check_structural_consistency(self, rendered: str, results: Dict) -> Dict:
        """Check structural consistency of the output"""
        # Check for consistent section markers
        sections = re.findall(r'^Section \d+', rendered, re.MULTILINE)
        if sections:
            unique_sections = len(set(sections))
            expected_sections = 9  # For KI summary
            if unique_sections != expected_sections:
                results["warnings"].append(
                    f"Section count mismatch: found {unique_sections}, expected {expected_sections}"
                )
        
        # Check for consistent paragraph structure
        paragraphs = rendered.split('\n\n')
        paragraph_lengths = [len(p.split()) for p in paragraphs if p.strip()]
        
        if paragraph_lengths:
            avg_length = np.mean(paragraph_lengths)
            std_length = np.std(paragraph_lengths)
            cv = (std_length / avg_length * 100) if avg_length > 0 else 0
            
            results["content_analysis"]["paragraph_cv"] = cv
            if cv > 50:  # High variability
                results["info"].append(f"High paragraph length variability: CV={cv:.1f}%")
        
        return results
    
    def _check_sentence_quality(self, rendered: str, results: Dict) -> Dict:
        """Check sentence structure and quality"""
        sentences = re.split(r'[.!?]+', rendered)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        issues = []
        
        for sentence in sentences:
            # Check for sentences starting with lowercase
            if sentence and not sentence[0].isupper() and not sentence[0].isdigit():
                issues.append("Sentence starting with lowercase")
            
            # Check for very short sentences (likely fragments)
            if len(sentence.split()) < 3:
                issues.append("Very short sentence fragment")
            
            # Check for very long sentences
            if len(sentence.split()) > 50:
                issues.append("Excessively long sentence")
        
        if issues:
            unique_issues = list(set(issues))
            results["warnings"].extend(unique_issues[:3])  # Limit to 3 unique issues
        
        results["content_analysis"]["sentence_count"] = len(sentences)
        
        return results
    
    def _check_consistency_thresholds(self, thresholds: Dict[str, float], 
                                     results: Dict) -> Dict:
        """Check if consistency thresholds are met"""
        if "min_extraction_score" in thresholds:
            # This would be populated by the extraction process
            pass
        
        if "max_response_variation" in thresholds:
            # Check variation in responses
            pass
        
        if "required_cache_hit_rate" in thresholds:
            # This would be tracked during extraction
            pass
        
        return results
    
    def _track_consistency_metrics(self, rendered: str, document_type: str):
        """Track metrics for consistency analysis"""
        metrics = self.consistency_metrics[document_type]
        
        # Track content hash
        content_hash = hashlib.md5(rendered.encode()).hexdigest()[:8]
        metrics.content_hashes.append(content_hash)
        
        # Track word count
        word_count = len(rendered.split())
        metrics.word_counts.append(word_count)
        
        # Track sentence count
        sentence_count = len(re.split(r'[.!?]+', rendered))
        metrics.sentence_counts.append(sentence_count)
    
    def _calculate_consistency_score(self, document_type: str) -> Dict[str, Any]:
        """Calculate overall consistency metrics"""
        metrics = self.consistency_metrics[document_type]
        
        if len(metrics.word_counts) < 2:
            return {
                "runs_analyzed": len(metrics.word_counts),
                "insufficient_data": True
            }
        
        cv = metrics.calculate_coefficient_of_variation()
        structural = metrics.calculate_structural_consistency()
        
        return {
            "runs_analyzed": len(metrics.word_counts),
            "coefficient_of_variation": cv,
            "structural_consistency": structural,
            "mean_word_count": np.mean(metrics.word_counts),
            "std_word_count": np.std(metrics.word_counts),
            "unique_outputs": len(set(metrics.content_hashes)),
            "target_achieved": cv < 15.0  # Target CV < 15%
        }
    
    def get_consistency_report(self, document_type: str = None) -> Dict[str, Any]:
        """Generate comprehensive consistency report"""
        report = {
            "overall_metrics": {},
            "by_document_type": {}
        }
        
        if document_type:
            types = [document_type]
        else:
            types = list(self.consistency_metrics.keys())
        
        for doc_type in types:
            metrics = self.consistency_metrics[doc_type]
            if len(metrics.word_counts) > 0:
                report["by_document_type"][doc_type] = {
                    "runs": len(metrics.word_counts),
                    "cv": metrics.calculate_coefficient_of_variation(),
                    "structural_consistency": metrics.calculate_structural_consistency(),
                    "mean_word_count": np.mean(metrics.word_counts),
                    "unique_outputs": len(set(metrics.content_hashes))
                }
        
        # Calculate overall metrics
        all_cvs = [m["cv"] for m in report["by_document_type"].values()]
        if all_cvs:
            report["overall_metrics"] = {
                "mean_cv": np.mean(all_cvs),
                "meets_target": np.mean(all_cvs) < 15.0,
                "document_types_analyzed": len(types)
            }
        
        return report


# For backward compatibility
ValidationOrchestrator = EnhancedValidationOrchestrator


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