# CLAUDE.md

## Architecture Overview
This repository implements a sophisticated development environment with:
- Advanced Claude hooks system for session management
- Persistent memory layer for knowledge accumulation
- Discussion/Implementation mode switching (DAIC)
- Automated task tracking and context refinement
- Centralized configuration management for all system parameters
- Structured logging framework with rotating file handlers
- Enhanced multi-agent system with LLM integration
- Comprehensive test fixtures for consistent testing

## Repository Structure
- `.claude/hooks/` - Claude Code integration scripts
- `.claude/state/` - Session state and memory storage
- `.claude/agents/` - Custom agent definitions
- `sessions/` - Task-based work sessions
- `app/` - Document Generation Framework
  - `core/` - Core framework components (orchestration, validation, RAG)
  - `plugins/` - Document type plugins (informed_consent, clinical_protocol)
  - `templates/` - Jinja2 template files organized by document type
  - `config.py` - Centralized configuration management
  - `logger.py` - Application logging configuration
  - `main.py` - FastAPI application with CORS security
- `tests/` - Test infrastructure
  - `fixtures.py` - Reusable test fixtures and mock data
  - `test_utils.py` - Shared test utilities

## Persistent Memory System

### Overview
The memory system provides persistent knowledge storage across Claude sessions, implementing:
- JSON-based memory with entities, relations, and episodes
- Temporal decay for relevance scoring
- Automatic observation capture from tool use
- Semantic query interface for memory retrieval
- Privacy controls to avoid storing sensitive information

### Key Memory Components

#### Core Memory Functions (.claude/hooks/shared_state.py:125-351)
- `load_memory_index()` - Load current memory snapshot
- `save_memory_index(memory_data)` - Save memory state
- `add_memory_observation(entity_key, entity_type, observation, confidence, tags, source)` - Add entity observations
- `add_memory_episode(task_name, learnings, patterns, success)` - Record task completions
- `query_memory_semantic(query, memory_type)` - Search memory by content
- `get_contextual_memory(task_name, affected_files)` - Get task-relevant memory
- `calculate_memory_relevance(timestamp, access_count)` - Calculate relevance with decay

#### Automatic Capture (.claude/hooks/memory-capture.py)
- `capture_tool_observation(tool_name, file_path, operation)` - Auto-capture from tool use
- `capture_error_pattern(error_message, context)` - Record error patterns
- `capture_user_preference(preference, category)` - Store user preferences
- `capture_task_completion(task_name, success, learnings)` - Record episode data

#### Manual Updates (.claude/hooks/update_memory.py)
- Command-line utility for explicit memory updates
- Usage: `python .claude/hooks/update_memory.py --task "task-name" --learnings "learning1|learning2"`
- Supports preferences, observations, and episode recording

### Memory Storage Structure

#### Memory Index (.claude/state/memory/memory-index.json)
- **Entities**: Codebase artifacts, user preferences, patterns, bug solutions
- **Relations**: Dependencies, implementations, conflicts between entities
- **Episodes**: Task completions with learnings and detected patterns
- **Statistics**: Counters for entities, relations, episodes, observations

#### Configuration (.claude/state/memory/memory-config.json)
- Temporal decay settings (decay_lambda: 0.1)
- Privacy patterns to avoid storing sensitive data
- Memory size limits and thresholds
- Entity and relation type schemas

#### Event Logs
- `memory.jsonl` - Memory events log
- `memory-work.jsonl` - Work-related memory events

### Privacy and Security

#### Forbidden Patterns
Memory system automatically excludes:
- Passwords, API keys, secrets, tokens, credentials
- Environment variables: AWS_, OPENAI_, ANTHROPIC_, GITHUB_TOKEN
- Configurable via memory-config.json privacy settings

#### Data Retention
- Automatic purge after 90 days (configurable)
- Anonymization of sensitive content
- Local storage only - no external transmission

### Memory Integration Points

#### Hook Integration
- **post-tool-use.py:34-45** - Automatic capture from Edit, Write, Bash tools
- **context-refinement agent** - Stores discoveries in persistent memory
- **session-start.py** - Loads relevant memory for new sessions

#### Query Interface
Memory can be queried for:
- User preferences by category
- Codebase insights about specific files
- Error patterns and solutions
- Task learnings and patterns
- Workflow commands and procedures

### Configuration Options

#### Memory Settings
- `decay_lambda`: Controls temporal decay rate (default: 0.1)
- `decay_enabled`: Enable/disable temporal decay (default: true)
- `confidence_threshold`: Minimum confidence for retrieval (default: 0.5)
- `relevance_threshold`: Minimum relevance score (default: 0.3)
- `max_memory_size_mb`: Storage size limit (default: 10MB)

#### Entity Types
- `user_preference` - User coding preferences and workflows
- `codebase_artifact` - File and component insights
- `pattern` - Detected development patterns
- `bug_solution` - Error patterns and solutions
- `workflow` - Procedural knowledge and commands

### Usage Examples

#### Querying Memory
```python
from shared_state import query_memory_semantic, get_contextual_memory

# Find testing preferences
results = query_memory_semantic("testing", "user_preference")

# Get context for current task
context = get_contextual_memory("feature-implementation", ["app.py", "routes.py"])
```

#### Manual Memory Updates
```bash
# Record task learnings
python .claude/hooks/update_memory.py --task "implement-auth" --learnings "JWT tokens need 1hr expiry|Redis cache improves performance"

# Record user preference
python .claude/hooks/update_memory.py --task "setup" --preference "Prefer TypeScript over JavaScript"

# Record codebase observation
python .claude/hooks/update_memory.py --task "refactor" --entity "auth.py" --observation "Contains rate limiting logic"
```

## Configuration Management

### Overview
Centralized configuration system in `app/config.py` manages all application settings, replacing hardcoded values throughout the codebase.

### Configuration Categories

#### Memory Configuration (`app/config.py:16-25`)
```python
MEMORY_CONFIG = {
    "max_entities": 5000,
    "max_episodes": 1000,
    "max_observations_per_entity": 100,
    "max_memory_size_mb": 10,
    "decay_lambda": 0.1,
    "decay_enabled": True,
    "confidence_threshold": 0.5,
    "relevance_threshold": 0.3,
}
```

#### Text Processing (`app/config.py:28-37`)
```python
TEXT_PROCESSING = {
    "max_tokens_per_batch": 18000,
    "truncation_limits": {
        "short": 150,
        "medium": 200,
        "long": 4000,
        "extra_long": 8000
    },
    "chunk_size": 2000,
}
```

#### CORS Security (`app/config.py:60-65`)
- Environment-based origin configuration
- Replaces insecure wildcard `["*"]` setting
- Credential support with controlled headers

#### Rate Limiting (`app/config.py:83-87`)
- Request throttling per minute/hour
- Burst size control for API protection

### Usage
```python
from config import MEMORY_CONFIG, TEXT_PROCESSING, get_test_pdf_path

# Access configuration values
max_entities = MEMORY_CONFIG["max_entities"]
pdf_path = get_test_pdf_path()
```

## Logging Framework

### Overview
Structured logging system in `app/logger.py` provides consistent logging across the application.

### Features
- Module-specific logger creation
- Rotating file handlers with size management (10MB default)
- Console and file output with configurable levels
- Consistent formatting across all modules

### Usage
```python
from logger import get_logger

logger = get_logger("module.name")
logger.info("Processing document")
logger.error(f"Failed to process: {error}")
```

### Configuration (`app/config.py:90-96`)
```python
LOGGING_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "app.log",
    "max_bytes": 10485760,  # 10MB
    "backup_count": 5,
}
```

## DAIC Mode System

### Mode Management (.claude/hooks/shared_state.py:33-91)
- **Discussion Mode**: Focus on planning and discussion (default)
- **Implementation Mode**: Enable tool use for code changes
- Toggle with `daic` command or `toggle_daic_mode()` function

### Integration with Memory
- Tool use captured only in Implementation mode
- Memory queries available in both modes
- Context refinement runs after Implementation sessions

## Task State Management

### Current Task Tracking (.claude/hooks/shared_state.py:94-123)
- `get_task_state()` - Current task, branch, affected services
- `set_task_state(task, branch, services)` - Set task context
- `add_service_to_task(service)` - Track affected services

### Session Integration
- Task state drives memory context
- Affected services tracked for documentation updates
- Branch information maintained for git operations

## Key Patterns

### Memory-Driven Development
- Tool use automatically captured in memory
- User preferences accumulated over time
- Error patterns stored for future reference
- Task learnings preserved across sessions

### Context Refinement
- Automatic discovery capture during implementation
- Context drift detection and documentation
- Institutional knowledge preservation

## Document Generation Framework

### Overview
The repository includes a sophisticated document generation framework that transforms regulatory documents into structured summaries. The framework uses a plugin-based architecture with multi-agent orchestration, Jinja2 templates, and RAG-based document processing.

### Core Components

#### DocumentGenerationFramework (`app/core/document_framework.py`)
Main orchestrator that coordinates plugin selection, template rendering, agent orchestration, and validation. Supports streaming RAG with SPLICE chunking for optimal performance.

#### PluginManager (`app/core/plugin_manager.py`)
Runtime plugin discovery and management system. Automatically loads document plugins from `app/plugins/` directory.

#### ValidationOrchestrator (`app/core/document_framework.py`)
Enhanced validation system with:
- Consistency metrics tracking (CV < 15% target)
- Critical value preservation
- Intent validation
- Prohibited phrase detection

#### MultiAgentPool (`app/core/multi_agent_system.py`)
Enhanced orchestration system with LLM integration for document processing:
- **ExtractionAgent** - Extracts information from documents using regex patterns
- **GenerationAgent** - LLM-powered content generation (lines 114-186)
  - Accepts optional LLM parameter for intelligent generation
  - Falls back to template-based generation if no LLM available
  - Generates context-aware introductions and participation details
- **ValidationAgent** - Validates output and preserves intent
- **IntentPreservationAgent** - Ensures semantic equivalence in generated content
- **SpecialistAgent** - Domain-specific processing
- **OrchestrationAgent** - Coordinates agent interactions

```python
# LLM integration in MultiAgentPool
agent_pool = MultiAgentPool(llm=llm_instance)
```

### Available Document Types

#### Informed Consent KI Summary
- Generates IRB-compliant Key Information summaries
- 9-section structured output format
- Template slots: BOOLEAN, ENUM, LIMITED_TEXT, NUMERIC, EXTRACTED
- Backward compatible with legacy `/uploadfile/` endpoint

#### Clinical Protocol
- Supports full 7-step clinical protocol workflow
- Sub-template selection based on:
  - Regulatory section (device/drug/biologic)
  - Therapeutic area (cardiovascular/oncology/etc)
  - Study phase (early/pivotal)
- 11+ standard sections with value propagation
- Critical value preservation for regulatory compliance

### API Endpoints

```python
# New unified generation endpoint
POST /generate/
{
  "document_type": "clinical-protocol",
  "parameters": {...},
  "file": <uploaded_file>
}

# List available document types
GET /document-types/

# Get plugin information
GET /document-types/{type}/

# Legacy endpoint (maintained for backward compatibility)
POST /uploadfile/
```

### Plugin Architecture

Each document type is implemented as a plugin extending `DocumentPlugin`:

```python
class DocumentPlugin(ABC):
    @abstractmethod
    def get_template_catalog(self) -> TemplateCatalog
    
    @abstractmethod
    def get_specialized_agents(self) -> List[Agent]
    
    @abstractmethod
    def get_validation_rules(self) -> ValidationRuleSet
    
    @abstractmethod
    def supports_document_type(self, doc_type: str) -> bool
```

### Template System

#### Jinja2 Templates
- Master templates in `app/templates/base/`
- Document-specific templates organized by type
- Template inheritance for code reuse
- Custom filters for content processing

#### Template Structure
```
app/templates/
├── base/
│   └── master.j2              # Base template with common elements
├── informed-consent/
│   ├── ki-summary.j2          # Key Information summary template
│   └── sections/              # Individual section templates
└── clinical-protocol/
    ├── master-protocol.j2     # Base clinical protocol
    ├── device-ide.j2          # Device-specific sections
    ├── drug-ind.j2            # Drug-specific sections
    └── biologic-ind.j2        # Biologic-specific sections
```

### Validation & Consistency

#### ConsistencyValidator (`app/core/consistency_validator.py`)
- Response cleaning and normalization
- Format-specific validation (BOOLEAN, ENUM, etc.)
- Prohibited phrase detection and removal
- LLM artifact cleaning

#### ConsistencyMetrics
- Coefficient of Variation (CV) tracking
- Structural consistency checking
- Content hash generation
- Multi-run consistency analysis

### Usage Examples

#### Generate Clinical Protocol
```python
from app.core.document_framework import DocumentGenerationFramework

framework = DocumentGenerationFramework()
result = await framework.generate(
    document_type="clinical-protocol",
    parameters={
        "regulatory_section": "device",
        "therapeutic_area": "cardiovascular",
        "study_phase": "pivotal"
    }
)
```

#### Create New Plugin
```python
from app.plugins.base import DocumentPlugin

class MyDocumentPlugin(DocumentPlugin):
    def get_document_types(self):
        return ["my-document-type"]
    
    def get_template_catalog(self):
        return TemplateCatalog(
            templates={"main": "templates/my-doc/main.j2"}
        )
```

## Related Documentation
- `.claude/agents/context-refinement.md` - Context update agent
- `.claude/state/memory/memory-config.json` - Memory configuration
- `sessions/` - Individual task documentation
- `sessions/tasks/h-refactor-generalize-document-summary-system.md` - Framework implementation details

## Testing

### Test Infrastructure
- Memory system tests: `.claude/hooks/test_memory.py`
- Knowledge capture tests: `.claude/hooks/test_knowledge_capture.py`
- Document generation tests: `test_ki_summary.py`, `test_clinical_protocol.py`
- Consistency validation: `test_consistency.py`

### Test Fixtures (`tests/fixtures.py`)
Comprehensive test fixture system for consistent testing:

#### MockPDFData
Provides realistic test data for different document types:
- Informed consent documents with IRB protocol data
- Clinical protocol documents with study design information

#### TestFixtures Manager
```python
from tests.fixtures import create_test_fixtures

fixtures = create_test_fixtures()
fixtures.setup()

# Create mock document
mock_doc = fixtures.create_mock_document("informed_consent")

# Create test PDF
test_pdf = fixtures.create_test_pdf("test.pdf")

# Get mock LLM
mock_llm = fixtures.mock_llm

fixtures.teardown()
```

#### Mock Models
- **Mock LLM**: Context-aware response generation without API calls
- **Mock Embedding Model**: Deterministic embeddings for testing

### Test Utilities (`tests/test_utils.py`)
Shared utilities integrated with centralized configuration:
- `setup_azure_openai()` - Uses config for Azure OpenAI setup
- `convert_numpy_types()` - Handles numpy type conversion
- `calculate_content_hash()` - Generates consistent content hashes

### Running Tests
```bash
# Run memory tests
python .claude/hooks/test_memory.py

# Run document generation tests
python test_ki_summary.py
python test_clinical_protocol.py

# Run consistency tests with configuration
python test_consistency.py  # Uses default PDF from config
```