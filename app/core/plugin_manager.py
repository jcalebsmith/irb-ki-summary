"""
Plugin Manager for Document Generation Framework
Implements runtime discovery and management of document type plugins
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Type
from pathlib import Path
import importlib.util
import inspect
from enum import Enum
from .exceptions import PluginLoadError, PluginNotFoundError


class SlotType(Enum):
    """Extended slot types for template system"""
    STATIC = "static"  # Fixed text
    EXTRACTED = "extracted"  # Retrieved from document
    GENERATED = "generated"  # LLM-generated content
    CONDITIONAL = "conditional"  # Context-dependent
    PROPAGATED = "propagated"  # Cross-template value propagation


@dataclass
class TemplateSlot:
    """Enhanced template slot with propagation support"""
    name: str
    slot_type: SlotType
    extraction_query: str
    validation_rules: Dict[str, Any]
    default_value: Optional[str] = None
    max_length: Optional[int] = None
    cross_reference_slots: List[str] = None  # For value propagation
    intent_preservation: bool = False  # Critical values that must not change
    fallback_strategy: Optional[str] = None
    
    def __post_init__(self):
        if self.cross_reference_slots is None:
            self.cross_reference_slots = []


@dataclass
class ValidationRuleSet:
    """Validation rules for document generation"""
    required_fields: List[str]
    max_lengths: Dict[str, int]
    allowed_values: Dict[str, List[str]]
    custom_validators: List[str]  # Function names to call
    intent_critical_fields: List[str]  # Fields that must preserve original intent


@dataclass
class TemplateCatalog:
    """Catalog of available templates for a document type"""
    templates: Dict[str, str]  # template_id -> template_path
    default_template: str
    metadata: Dict[str, Any]
    
    def get_template(self, template_id: str = None) -> str:
        """Get template path by ID or return default"""
        if template_id and template_id in self.templates:
            return self.templates[template_id]
        return self.templates.get(self.default_template, "")


class DocumentPlugin(ABC):
    """Abstract base class for document generation plugins"""
    
    @abstractmethod
    def get_plugin_info(self) -> Dict[str, Any]:
        """Return plugin metadata"""
        pass
    
    @abstractmethod
    def get_template_catalog(self) -> TemplateCatalog:
        """Return available templates for this plugin"""
        pass
    
    @abstractmethod
    def get_specialized_agents(self) -> List[Any]:
        """Return list of specialized agents for this document type"""
        pass
    
    @abstractmethod
    def get_validation_rules(self) -> ValidationRuleSet:
        """Return validation rules for this document type"""
        pass
    
    @abstractmethod
    def supports_document_type(self, doc_type: str) -> bool:
        """Check if this plugin supports the given document type"""
        pass
    
    @abstractmethod
    def get_sub_template_rules(self) -> Dict[str, Any]:
        """Return rules for sub-template selection"""
        pass
    
    @abstractmethod
    def get_critical_values(self) -> List[str]:
        """Return list of critical values that must be preserved"""
        pass
    
    @abstractmethod
    def resolve_template(self, parameters: Dict[str, Any]) -> str:
        """Resolve which template to use based on parameters"""
        pass


class PluginManager:
    """
    Manages document generation plugins with runtime discovery
    """
    
    def __init__(self, plugin_dir: str = "app/plugins"):
        self.plugin_dir = Path(plugin_dir)
        self.plugins: Dict[str, DocumentPlugin] = {}
        self.plugin_registry: Dict[str, Type[DocumentPlugin]] = {}
        self._discover_plugins()
    
    def _discover_plugins(self):
        """Discover and load plugins from plugin directory"""
        if not self.plugin_dir.exists():
            self.plugin_dir.mkdir(parents=True, exist_ok=True)
            return
        
        # Look for Python files in plugin directory
        for plugin_file in self.plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue  # Skip private modules
            
            try:
                # Load the module
                spec = importlib.util.spec_from_file_location(
                    plugin_file.stem, plugin_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find DocumentPlugin subclasses
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, DocumentPlugin) and 
                            obj != DocumentPlugin):
                            
                            # Register the plugin class
                            plugin_instance = obj()
                            plugin_info = plugin_instance.get_plugin_info()
                            plugin_id = plugin_info.get("id", name.lower())
                            
                            self.plugin_registry[plugin_id] = obj
                            self.plugins[plugin_id] = plugin_instance
                            
                            print(f"Discovered plugin: {plugin_id} from {plugin_file.name}")
            
            except Exception as e:
                # Log error but don't fail the entire loading process
                print(f"Warning: Could not load plugin from {plugin_file}: {e}")
                # Continue loading other plugins
    
    def get_plugin(self, document_type: str) -> Optional[DocumentPlugin]:
        """
        Get plugin that supports the given document type
        """
        # First check if document_type is a plugin ID
        if document_type in self.plugins:
            return self.plugins[document_type]
        
        # Otherwise find a plugin that supports this document type
        for plugin_id, plugin in self.plugins.items():
            if plugin.supports_document_type(document_type):
                return plugin
        
        return None
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all available plugins and their info"""
        plugin_list = []
        for plugin_id, plugin in self.plugins.items():
            info = plugin.get_plugin_info()
            info["id"] = plugin_id
            plugin_list.append(info)
        return plugin_list
    
    def register_plugin(self, plugin_id: str, plugin_class: Type[DocumentPlugin]):
        """Manually register a plugin"""
        plugin_instance = plugin_class()
        self.plugin_registry[plugin_id] = plugin_class
        self.plugins[plugin_id] = plugin_instance
    
    def reload_plugins(self):
        """Reload all plugins (useful for development)"""
        self.plugins.clear()
        self.plugin_registry.clear()
        self._discover_plugins()
    
    def get_supported_document_types(self) -> List[str]:
        """Get list of all supported document types across all plugins"""
        supported_types = set()
        for plugin in self.plugins.values():
            plugin_info = plugin.get_plugin_info()
            if "supported_types" in plugin_info:
                supported_types.update(plugin_info["supported_types"])
        return sorted(list(supported_types))