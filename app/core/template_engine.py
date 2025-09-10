"""
Jinja2-based Template Engine for Document Generation
Supports template inheritance, custom filters, and value propagation
"""
from jinja2 import Environment, FileSystemLoader, Template, select_autoescape
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import re
import sys
sys.path.append(str(Path(__file__).parent.parent))
from logger import get_logger
from .exceptions import TemplateError, TemplateNotFoundError, TemplateRenderError

# Set up module logger
logger = get_logger("core.template_engine")


class Jinja2Engine:
    """
    Template engine using Jinja2 with support for inheritance and custom filters
    """
    
    def __init__(self, template_dir: str = "app/templates"):
        self.template_dir = Path(template_dir)
        self.env = self._setup_environment()
        self.global_parameters: Dict[str, Any] = {}
        
    def _setup_environment(self) -> Environment:
        """Set up Jinja2 environment with custom configuration"""
        # Create template directory structure if it doesn't exist
        if not self.template_dir.exists():
            self._create_template_structure()
        
        # Configure Jinja2 environment
        env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        
        # Add custom filters
        env.filters['capitalize_first'] = self._capitalize_first
        env.filters['remove_duplicates'] = self._remove_duplicate_phrases
        env.filters['limit_words'] = self._limit_words
        env.filters['format_list'] = self._format_list
        env.filters['ensure_period'] = self._ensure_period
        
        # Add custom globals
        
        return env
    
    def _create_template_structure(self):
        """Create default template directory structure"""
        # Create base structure
        base_dir = self.template_dir / "base"
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create master template
        master_template = base_dir / "master.j2"
        if not master_template.exists():
            master_template.write_text("""
{# Master template for all document types #}
{% block document_header %}
{# Document header - can be overridden #}
{% endblock %}

{% block document_body %}
{# Main document content #}
{% endblock %}

{% block document_footer %}
{# Document footer - can be overridden #}
{% endblock %}
""")
        
        # Create validators template
        validators_template = base_dir / "validators.j2"
        if not validators_template.exists():
            validators_template.write_text("""
{# Common validation macros #}

{% macro validate_required(value, field_name) %}
  {% if not value %}
    {{ raise_error(field_name ~ " is required") }}
  {% endif %}
{% endmacro %}

{% macro validate_length(value, max_length, field_name) %}
  {% if value and value|length > max_length %}
    {{ raise_error(field_name ~ " exceeds maximum length of " ~ max_length) }}
  {% endif %}
{% endmacro %}

{% macro validate_options(value, allowed_values, field_name) %}
  {% if value and value not in allowed_values %}
    {{ raise_error(field_name ~ " must be one of: " ~ allowed_values|join(", ")) }}
  {% endif %}
{% endmacro %}
""")
        
        # Create informed consent directory
        ic_dir = self.template_dir / "informed-consent"
        ic_dir.mkdir(exist_ok=True)
        
        # Create sections directory
        sections_dir = ic_dir / "sections"
        sections_dir.mkdir(exist_ok=True)
    
    def render(self, 
               template_path: str, 
               context: Dict[str, Any],
               globals: Optional[Dict[str, Any]] = None) -> str:
        """
        Render a template with the given context
        
        Args:
            template_path: Path to template relative to template_dir
            context: Template context variables
            globals: Additional global variables
            
        Returns:
            Rendered template string
        """
        try:
            logger.debug(f"Template engine - trying to load template: {template_path}")
            template = self.env.get_template(template_path)
            logger.debug(f"Template loaded successfully")
            
            # Merge global parameters
            full_context = {**self.global_parameters}
            full_context.update(context)
            
            # If generated_content exists, merge it into top-level context for template access
            if 'generated_content' in context and isinstance(context['generated_content'], dict):
                full_context.update(context['generated_content'])
            
            if globals:
                full_context.update(globals)
            
            logger.debug(f"Rendering template with context keys: {list(full_context.keys())}")
            result = template.render(full_context)
            logger.debug(f"Template rendered, result length: {len(result) if result else 0}")
            logger.debug(f"Template engine returning result type: {type(result)}")
            logger.debug(f"First 100 chars of result: {result[:100] if result else 'None'}")
            return result
        except FileNotFoundError as e:
            raise TemplateNotFoundError(template_path)
        except Exception as e:
            raise TemplateRenderError(
                template_path,
                f"Failed to render template: {str(e)}"
            )
    
    def render_string(self, template_string: str, context: Dict[str, Any]) -> str:
        """Render a template from a string"""
        template = self.env.from_string(template_string)
        full_context = {**self.global_parameters, **context}
        return template.render(full_context)
    
    def set_global_parameters(self, params: Dict[str, Any]):
        """Set global parameters available to all templates"""
        self.global_parameters.update(params)
    
    
    # Custom filter functions
    @staticmethod
    def _capitalize_first(text: str) -> str:
        """Capitalize only the first letter of the text"""
        if not text:
            return text
        return text[0].upper() + text[1:]
    
    @staticmethod
    def _remove_duplicate_phrases(text: str) -> str:
        """Remove duplicate phrases from text"""
        sentences = text.split('. ')
        unique_sentences = []
        for sentence in sentences:
            if sentence not in unique_sentences:
                unique_sentences.append(sentence)
        return '. '.join(unique_sentences)
    
    @staticmethod
    def _limit_words(text: str, word_limit: int) -> str:
        """Limit text to a specific number of words"""
        words = text.split()
        if len(words) <= word_limit:
            return text
        return ' '.join(words[:word_limit]) + '...'
    
    @staticmethod
    def _format_list(items: List[str], separator: str = ", ", last_sep: str = " and ") -> str:
        """Format a list of items with proper separators"""
        if not items:
            return ""
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return f"{items[0]}{last_sep}{items[1]}"
        return separator.join(items[:-1]) + last_sep + items[-1]
    
    @staticmethod
    def _ensure_period(text: str) -> str:
        """Ensure text ends with a period"""
        if not text:
            return text
        text = text.rstrip()
        if text and text[-1] not in '.!?':
            return text + '.'
        return text

    @staticmethod
    def _fix_articles(text: str) -> str:
        # Deprecated: rely on LLM to produce natural phrasing
        return text
    
    def create_template_from_slots(self, 
                                   template_text: str, 
                                   slots: List[Any]) -> Template:
        """
        Create a Jinja2 template from slot-based template text
        
        Args:
            template_text: Template text with {slot_name} placeholders
            slots: List of TemplateSlot objects
            
        Returns:
            Jinja2 Template object
        """
        # Convert {slot_name} to {{ slot_name }} for Jinja2
        jinja_template_text = re.sub(
            r'\{(\w+)\}',
            r'{{ \1 }}',
            template_text
        )
        
        # Add validation for required slots
        slot_names = [slot.name for slot in slots if hasattr(slot, 'name')]
        validation_block = "{% import 'base/validators.j2' as validators %}\n"
        
        for slot in slots:
            if hasattr(slot, 'validation_rules'):
                rules = slot.validation_rules
                if rules.get('required'):
                    validation_block += f"{{% call validators.validate_required({slot.name}, '{slot.name}') %}}{{% endcall %}}\n"
                if 'max_length' in rules:
                    validation_block += f"{{% call validators.validate_length({slot.name}, {rules['max_length']}, '{slot.name}') %}}{{% endcall %}}\n"
        
        # Combine validation and template
        full_template = validation_block + jinja_template_text
        
        return self.env.from_string(full_template)
    
    def list_available_templates(self) -> List[str]:
        """List all available templates"""
        templates = []
        for template_file in self.template_dir.rglob("*.j2"):
            relative_path = template_file.relative_to(self.template_dir)
            templates.append(str(relative_path))
        return sorted(templates)
