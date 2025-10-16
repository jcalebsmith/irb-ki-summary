---
task: h-refactor-app-comprehensive-cleanup
branch: feature/refactor-app-comprehensive-cleanup
status: pending
created: 2025-09-12
modules: [config, core, plugins, main, logger, pdf, summary]
---

# Comprehensive App Refactoring and Cleanup

## Problem/Goal
The app/ folder needs a comprehensive refactoring to:
- Remove unnecessary complexity and simplify the codebase
- Replace all stubs, placeholders, and TODOs with real implementation
- Remove deprecated and orphaned code
- Eliminate technical debt
- Fix code smells and anti-patterns
- Ensure OpenAI Python SDK best practices using official conventions
- Prefer framework solutions over custom code
- Create thorough integration tests with real data and API calls (no mocks)
- Achieve simplicity and elegance in the codebase
- Make code easy to understand, maintain, and extend

## Success Criteria
- [ ] All modules in app/ reviewed and refactored for simplicity
- [ ] All TODO comments replaced with working implementation
- [ ] All placeholder/stub code replaced with real functionality
- [ ] Deprecated and orphaned code removed
- [ ] Code smells and anti-patterns eliminated
- [ ] OpenAI SDK usage follows official best practices (verified via context7)
- [ ] Framework solutions used instead of custom implementations where applicable
- [ ] Comprehensive integration tests created using real data and API calls
- [ ] No mock objects in integration tests
- [ ] Code passes all linting and type checking
- [ ] Documentation updated to reflect changes
- [ ] All tests passing with real API connections

## Context Manifest

### Architecture Overview
The app/ folder contains a sophisticated document generation framework that processes regulatory documents (informed consent, clinical protocols) into structured summaries. The system uses a plugin-based architecture with multi-agent orchestration and Jinja2 templating.

### Current System Flow
1. **API Layer** (app/main.py) - FastAPI endpoints receive PDF uploads
2. **Document Framework** (app/core/document_framework.py) - Orchestrates plugin-based processing
3. **Multi-Agent System** (app/core/multi_agent_system.py) - 6+ agent types handle extraction and generation
4. **Evidence Pipeline** (app/core/evidence_pipeline.py, 936 lines) - Complex LLM-based extraction
5. **Template Engine** (app/core/template_engine.py) - Renders output using Jinja2
6. **Validation Framework** - Multiple validation layers ensure quality

### Technical Debt Analysis

#### 1. Excessive Complexity
- **app/core/evidence_pipeline.py:936 lines** - Overly complex extraction logic
- **app/core/multi_agent_system.py:500+ lines** - Too many agent types with overlapping responsibilities
- **Multiple extraction patterns**: Regex-based, evidence-based, LLM-based all coexist

#### 2. Debug Code in Production
- **app/core/evidence_extraction_agent.py:234** - Print statements left in code
- **app/core/llm_integration.py:156** - Bare except clauses
- **app/core/document_framework.py:412** - TODO comments throughout

#### 3. Configuration Issues
- **app/main.py:45** - Hardcoded values despite centralized config
- **app/core/llm_integration.py:78** - API keys directly in code
- **app/config.py** - Not consistently used across modules

#### 4. Redundant Code
- **app/core/simple_extraction.py** vs **app/core/evidence_extraction_agent.py** - Duplicate extraction logic
- **app/core/validators.py** vs **app/core/semantic_validation.py** - Overlapping validation
- **app/core/extraction_models.py** vs **app/core/evidence_models.py** - Similar data models

### Key Dependencies
- **Azure OpenAI API** - Used for LLM operations
- **Jinja2** - Template rendering
- **FastAPI** - API framework
- **Pydantic** - Data validation
- **PyPDF2** - PDF processing

### Integration Points to Preserve
- **/generate/** endpoint - Main document generation API
- **/uploadfile/** endpoint - Legacy compatibility
- **Plugin discovery mechanism** - Dynamic plugin loading
- **Template inheritance structure** - Base templates in app/templates/base/

### Context Files
- @app/core/document_framework.py - Main orchestration logic
- @app/core/multi_agent_system.py:114-186 - Agent pool with LLM integration
- @app/core/evidence_pipeline.py - Complex extraction to simplify
- @app/core/llm_integration.py - Needs SDK update
- @app/main.py - API endpoints and configuration
- @app/config.py - Centralized configuration (underutilized)
- @app/plugins/informed_consent_plugin.py - Plugin implementation pattern
- @app/core/template_engine.py - Template processing logic

### Immediate Concerns
1. **Debug artifacts** throughout production code
2. **No real integration tests** - All tests use mocks
3. **Inconsistent error handling** - Mix of approaches
4. **Performance issues** - No caching, inefficient loops
5. **Security concerns** - API keys in code, no rate limiting

### Simplification Opportunities
- **Reduce code by 50-70%** by consolidating duplicate functionality
- **Single extraction pipeline** instead of multiple approaches
- **3-4 focused agents** instead of 6+ overlapping ones
- **Modern OpenAI SDK patterns** with structured outputs
- **Pydantic Settings** for all configuration

## Subtasks
1. **Core Module Analysis** - Review and catalog all core modules
2. **Plugin System Refactoring** - Simplify plugin architecture
3. **LLM Integration Cleanup** - Update to latest OpenAI SDK patterns
4. **Evidence Pipeline Refactoring** - Remove complexity from evidence extraction
5. **Multi-Agent System Simplification** - Streamline agent orchestration
6. **Template Engine Optimization** - Simplify template processing
7. **Validation Framework Cleanup** - Consolidate validation logic
8. **API Endpoint Refactoring** - Clean up FastAPI implementation
9. **Integration Test Suite** - Create comprehensive real-data tests
10. **Configuration Management** - Ensure centralized config usage
11. **Logging Framework** - Verify consistent logging patterns
12. **Final Code Review** - Ensure all criteria met

## User Notes
- Focus on simplicity and elegance
- Use context7 to verify OpenAI SDK best practices
- Real integration tests are critical - no mocks allowed
- Each file should be reviewed for unnecessary complexity
- Prefer deletion over keeping questionable code
- Framework solutions should be preferred over custom implementations

## Work Log
- [2025-09-12] Task created for comprehensive app/ refactoring