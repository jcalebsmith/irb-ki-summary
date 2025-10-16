"""
Simplified Jinja2 Template Renderer
Clean implementation focused on essential functionality
"""
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Dict, Any, List
from pathlib import Path
from app.core.exceptions import TemplateError, TemplateNotFoundError
from app.logger import get_logger

logger = get_logger("core.template_renderer")


class SimpleTemplateRenderer:
    """
    Simplified template renderer using Jinja2.
    Reduces from 264 lines to ~80 lines.
    """
    
    def __init__(self, template_dir: str = "app/templates"):
        """
        Initialize template renderer.
        
        Args:
            template_dir: Directory containing templates
        """
        self.template_dir = Path(template_dir)
        
        # Ensure template directory exists
        if not self.template_dir.exists():
            self.template_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Created template directory: {self.template_dir}")
        
        # Configure Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Register essential custom filters
        self.env.filters['limit_words'] = self._limit_words
        self.env.filters['ensure_period'] = self._ensure_period
    
    def render(self, template_path: str, context: Dict[str, Any]) -> str:
        """
        Render a template with context.
        
        Args:
            template_path: Path to template relative to template_dir
            context: Template variables
            
        Returns:
            Rendered template string
            
        Raises:
            TemplateNotFoundError: If template not found
            TemplateError: If rendering fails
        """
        try:
            template = self.env.get_template(template_path)
            
            # Flatten nested context for easier access in templates
            flat_context = self._flatten_context(context)
            
            return template.render(flat_context)
            
        except FileNotFoundError:
            raise TemplateNotFoundError(f"Template not found: {template_path}")
        except Exception as e:
            raise TemplateError(f"Failed to render {template_path}: {e}")
    
    def _flatten_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested context for template access"""
        flat = dict(context)
        
        # Merge extracted values first, then allow generated content to override
        if 'extracted_values' in context and isinstance(context['extracted_values'], dict):
            flat.update(context['extracted_values'])
        
        if 'generated_content' in context and isinstance(context['generated_content'], dict):
            flat.update(context['generated_content'])
        
        return flat
    
    @staticmethod
    def _limit_words(text: str, limit: int) -> str:
        """Limit text to specified number of words"""
        words = text.split()
        if len(words) <= limit:
            return text
        return ' '.join(words[:limit]) + '...'
    
    @staticmethod
    def _ensure_period(text: str) -> str:
        """Ensure text ends with proper punctuation"""
        if not text:
            return text
        text = text.rstrip()
        if text and text[-1] not in '.!?':
            return text + '.'
        return text
