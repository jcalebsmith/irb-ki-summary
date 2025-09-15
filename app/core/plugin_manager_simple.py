"""
Simplified Plugin Manager for Document Generation
Reduces complexity from 201 lines to ~100 lines
"""
from typing import Dict, List, Optional, Any, Type
from pathlib import Path
import importlib.util
import inspect
from app.core.plugin_base import SimpleDocumentPlugin
from app.core.exceptions import PluginNotFoundError
from app.logger import get_logger

logger = get_logger("core.plugin_manager")


class SimplePluginManager:
    """
    Simplified plugin manager with auto-discovery and minimal complexity.
    Reduces from 201 lines to ~100 lines.
    """
    
    def __init__(self, plugin_dir: str = "app/plugins"):
        """
        Initialize plugin manager.
        
        Args:
            plugin_dir: Directory containing plugin modules
        """
        self.plugin_dir = Path(plugin_dir)
        self.plugins: Dict[str, SimpleDocumentPlugin] = {}
        self._load_plugins()
    
    def _load_plugins(self) -> None:
        """Load all plugins from plugin directory"""
        if not self.plugin_dir.exists():
            logger.warning(f"Plugin directory {self.plugin_dir} does not exist")
            return
        
        # Find all Python files ending with _simple.py or plugin.py
        plugin_files = list(self.plugin_dir.glob("*_simple.py"))
        if not plugin_files:
            # Fallback to original plugin files
            plugin_files = list(self.plugin_dir.glob("*_plugin.py"))
        
        for plugin_file in plugin_files:
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
                    
                    # Find SimpleDocumentPlugin subclasses
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, SimpleDocumentPlugin) and 
                            obj != SimpleDocumentPlugin):
                            
                            # Create plugin instance
                            plugin = obj()
                            plugin_name = plugin.config.name
                            
                            # Register plugin for each supported type
                            for doc_type in plugin.config.supported_types:
                                self.plugins[doc_type.lower()] = plugin
                            
                            logger.info(f"Loaded plugin: {plugin_name} from {plugin_file.name}")
            
            except Exception as e:
                logger.error(f"Failed to load plugin from {plugin_file}: {e}")
    
    def get_plugin(self, document_type: str) -> Optional[SimpleDocumentPlugin]:
        """
        Get plugin for document type.
        
        Args:
            document_type: Type of document to process
            
        Returns:
            Plugin instance or None if not found
        """
        return self.plugins.get(document_type.lower())
    
    def list_supported_types(self) -> List[str]:
        """Get list of all supported document types"""
        return sorted(list(self.plugins.keys()))
    
    def get_plugin_info(self, document_type: str) -> Dict[str, Any]:
        """
        Get information about a plugin.
        
        Args:
            document_type: Type of document
            
        Returns:
            Plugin information dictionary
            
        Raises:
            PluginNotFoundError: If plugin not found
        """
        plugin = self.get_plugin(document_type)
        if not plugin:
            raise PluginNotFoundError(f"No plugin found for document type: {document_type}")
        return plugin.get_info()
    
    def register_plugin(self, plugin: SimpleDocumentPlugin) -> None:
        """
        Manually register a plugin.
        
        Args:
            plugin: Plugin instance to register
        """
        for doc_type in plugin.config.supported_types:
            self.plugins[doc_type.lower()] = plugin
        logger.info(f"Registered plugin: {plugin.config.name}")