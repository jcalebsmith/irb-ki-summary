# Developer Guide - Document Generation Framework

## 📚 Overview for Junior Developers

This guide helps new developers understand the Document Generation Framework, a system that transforms regulatory documents (like medical consent forms) into structured summaries using AI.

## 🏗️ Architecture Overview

```
User Request → FastAPI → Plugin Manager → Multi-Agent System → Template Engine → Validation → Response
```

### Key Components

1. **Plugin Manager** (`plugin_manager.py`)
   - Dynamically loads document type handlers
   - Each document type (e.g., informed consent, clinical protocol) is a plugin
   - Plugins define templates, extraction rules, and validation requirements

2. **Multi-Agent System** (`multi_agent_system.py`)
   - Different AI agents handle specific tasks:
     - ExtractionAgent: Pulls information from documents
     - GenerationAgent: Creates new content
     - ValidationAgent: Checks quality and compliance
   - Agents communicate through a shared context

3. **Template Engine** (`template_engine.py`)
   - Uses Jinja2 templates for document structure
   - Templates contain placeholders filled with extracted/generated content
   - Supports template inheritance for reusability

4. **RAG Pipeline** (`rag_pipeline.py`)
   - RAG = Retrieval-Augmented Generation
   - Chunks large documents into smaller pieces
   - Creates searchable index for efficient information retrieval
   - Uses "SPLICE" method for optimal chunk boundaries

5. **Document Framework** (`document_framework.py`)
   - Main orchestrator that coordinates all components
   - Follows a clear pipeline: Plugin → Process → Generate → Validate

## 🚀 Getting Started

### Understanding the Flow

1. **Plugin Discovery**: User calls `/plugins/` to see available plugins
2. **Request Arrives**: User uploads a PDF through `/generate/` with explicit `plugin_id`
3. **Plugin Selection**: System loads the specified plugin (no auto-detection)
4. **Document Processing**: PDF is converted to text and chunked for processing
5. **Agent Orchestration**: Multiple AI agents work together to extract and generate content
6. **Template Rendering**: Extracted values fill template placeholders
7. **Validation**: Output is checked for quality, consistency, and compliance
8. **Response**: Structured JSON with sections and texts

### API Usage Example

```python
import requests

# Step 1: Discover available plugins
response = requests.get("http://localhost:8000/plugins/")
plugins = response.json()["plugins"]
# Returns: [{"plugin_id": "informed-consent-ki", "info": {...}}, ...]

# Step 2: Choose a plugin and process document
with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/generate/",
        files={"file": f},
        data={
            "plugin_id": "informed-consent-ki",  # Required - explicit selection
            "parameters": "{}"
        }
    )
result = response.json()
```

### Code Example - Simple Plugin

```python
from app.core.plugin_manager import DocumentPlugin

class MySimplePlugin(DocumentPlugin):
    """Example plugin for junior developers."""
    
    def get_plugin_info(self):
        return {
            "id": "my-simple-plugin",
            "name": "Simple Document Plugin",
            "version": "1.0.0"
        }
    
    def get_template_catalog(self):
        # Define available templates
        return TemplateCatalog(
            templates={"default": "templates/simple.j2"},
            default_template="default",
            metadata={}
        )
    
    def get_validation_rules(self):
        # Define what makes a valid document
        return ValidationRuleSet(
            required_fields=["title", "content"],
            max_lengths={"title": 100, "content": 1000},
            allowed_values={},
            custom_validators=[],
            intent_critical_fields=["title"]
        )
```

## 📂 File Structure

```
app/
├── core/                   # Framework core
│   ├── types.py           # Type definitions (START HERE!)
│   ├── document_framework.py  # Main orchestrator
│   ├── plugin_manager.py      # Plugin system
│   ├── multi_agent_system.py  # AI agents
│   ├── template_engine.py     # Template rendering
│   └── rag_pipeline.py        # Document processing
├── plugins/               # Document type plugins
│   ├── informed_consent_plugin.py
│   └── clinical_protocol_plugin.py
├── templates/            # Jinja2 templates
└── main.py              # FastAPI application

```

## 🔑 Key Concepts

### 1. Type Safety
We use the `types.py` module to define clear data structures:
- `ValidationResult`: Structure for validation outcomes
- `ExtractionField`: Defines what to extract from documents
- `ProcessingError`: Custom exceptions with error codes

### 2. Constants Instead of Magic Numbers
All hardcoded values are in `types.py`:
- `ValidationConstants.TARGET_CV_PERCENTAGE = 15.0`
- `ProcessingConstants.DEFAULT_CHUNK_SIZE = 1024`

### 3. Error Handling
Use error codes for clear error identification:
```python
from app.core.types import ProcessingError, ErrorCodes

if not document:
    raise ProcessingError(
        error_code=ErrorCodes.DOC_INVALID_FORMAT,
        message="Document is required",
        details={"received": type(document)}
    )
```

### 4. Async/Await Pattern
Most operations are asynchronous for better performance:
```python
async def process_document(self, doc):
    # Async operations allow multiple tasks to run concurrently
    result = await self._extract_content(doc)
    return result
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
python test_unified_framework.py

# Test specific component
python -m pytest app/core/test_document_framework.py -v
```

### Writing Tests
```python
def test_validation_constants():
    """Test that validation constants are properly defined."""
    assert ValidationConstants.TARGET_CV_PERCENTAGE == 15.0
    assert len(ValidationConstants.PROHIBITED_PHRASES) > 0
```

## 🐛 Debugging Tips

1. **Enable Debug Logging**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Check Plugin Loading**
   ```python
   from app.core.document_framework import DocumentGenerationFramework
   framework = DocumentGenerationFramework()
   print(framework.list_supported_document_types())
   ```

3. **Validate Templates**
   - Templates are in `app/templates/`
   - Use `{{ variable }}` for placeholders
   - Check for typos in variable names

## 📖 Common Tasks

### Adding a New Document Type
1. Create a new plugin in `app/plugins/`
2. Define extraction schema
3. Create Jinja2 template
4. Add validation rules
5. Test with sample document

### Modifying Extraction Rules
1. Find the plugin file (e.g., `informed_consent_plugin.py`)
2. Update the `EXTRACTION_SCHEMA` dictionary
3. Test extraction with real documents

### Adjusting Validation
1. Open `types.py`
2. Modify constants in `ValidationConstants`
3. Update validation logic if needed

## 🤝 Best Practices

1. **Use Type Hints**: Always specify types for function parameters and returns
2. **Write Docstrings**: Explain what each function does and why
3. **Handle Errors Gracefully**: Use try-except blocks with specific error types
4. **Keep Functions Small**: Each function should do one thing well
5. **Test Your Changes**: Write tests for new functionality

## 📚 Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Jinja2 Template Guide](https://jinja.palletsprojects.com/)
- [Python Async/Await](https://docs.python.org/3/library/asyncio.html)
- [Type Hints in Python](https://docs.python.org/3/library/typing.html)

## 🆘 Getting Help

1. Check this guide first
2. Read the inline code comments
3. Look at existing plugins for examples
4. Ask senior developers for complex issues

Remember: The codebase is designed to be modular. Start by understanding one component before moving to the next!