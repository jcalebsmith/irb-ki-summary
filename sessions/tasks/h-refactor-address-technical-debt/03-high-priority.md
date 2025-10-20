---
subtask: 03-high-priority
parent: h-refactor-address-technical-debt
status: pending
estimated_hours: 6.5
---

# High-Priority Issues - Architecture & Configuration

## Goal
Fix architectural issues that cause deployment fragility and maintenance problems.

## Issues to Fix

### 1. Eliminate sys.path Manipulation (3 hours)
**Priority:** HIGH
**Files affected:**
- app/core/document_framework.py:15-17
- app/plugins/informed_consent/plugin.py:8-10
- app/plugins/clinical_protocol/plugin.py:8-10

**Current Problem:**
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))  # ANTI-PATTERN
```

**Impact:**
- Breaks module isolation
- Causes import errors in different environments
- Makes deployment fragile (works locally, fails in production)
- Prevents proper package installation

**Root Cause:**
Incorrect package structure or imports. Python should find modules through proper package hierarchy.

**Fix Strategy:**

#### Option A: Proper Package Structure (Recommended)
```python
# Ensure __init__.py exists in all directories
app/
  __init__.py
  core/
    __init__.py
  plugins/
    __init__.py
    informed_consent/
      __init__.py

# Use relative imports in plugins
from ..core.document_framework import DocumentFramework  # Relative
# OR
from app.core.document_framework import DocumentFramework  # Absolute

# Remove all sys.path manipulation
```

#### Option B: Install as Package
```bash
# Add setup.py or pyproject.toml
pip install -e .  # Editable install

# Then imports work naturally
from app.core.document_framework import DocumentFramework
```

**Implementation Steps:**
1. [ ] Audit all imports to understand dependency graph
2. [ ] Ensure __init__.py exists in all package directories
3. [ ] Convert sys.path hacks to proper imports
4. [ ] Test imports from different entry points
5. [ ] Update run_test.py and other scripts
6. [ ] Document import conventions

**Success Criteria:**
- [ ] No sys.path.insert() or sys.path.append() anywhere
- [ ] All imports work without path manipulation
- [ ] Tests pass from any directory
- [ ] Server starts from any location
- [ ] Docker deployment works (if applicable)

### 2. Standardize Configuration Management (2 hours)
**Priority:** HIGH
**Files affected:**
- app/main.py
- app/api.py
- app/config.py

**Current Problem:**
```python
# main.py - hardcoded
allow_origins=["http://localhost:3000"]

# api.py - environment-based
allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

# Inconsistent configuration access patterns
```

**Impact:**
- Configuration duplication
- Different behavior in main.py vs api.py
- Hard to manage multi-environment deployments
- No single source of truth

**Fix Strategy:**

Create centralized configuration manager:

```python
# app/config.py (enhance existing)

class AppConfig:
    """Centralized application configuration."""

    # Server
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "8000"))

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    CORS_CREDENTIALS = os.getenv("CORS_CREDENTIALS", "true").lower() == "true"

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "app.log")

    # Document Processing
    MAX_PDF_SIZE_MB = int(os.getenv("MAX_PDF_SIZE_MB", "10"))
    PROCESSING_TIMEOUT = int(os.getenv("PROCESSING_TIMEOUT", "60"))

    @classmethod
    def validate(cls):
        """Validate configuration on startup."""
        # Check required settings
        # Validate value ranges
        # Log configuration summary

# Use in main.py and api.py
from app.config import AppConfig

app.add_middleware(
    CORSMiddleware,
    allow_origins=AppConfig.CORS_ORIGINS,
    allow_credentials=AppConfig.CORS_CREDENTIALS,
)
```

**Environment File Template:**
```bash
# .env.example
HOST=127.0.0.1
PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
LOG_LEVEL=INFO
MAX_PDF_SIZE_MB=10
PROCESSING_TIMEOUT=60
```

**Success Criteria:**
- [ ] All configuration in AppConfig class
- [ ] No hardcoded values in application code
- [ ] .env.example with all settings
- [ ] Configuration validation on startup
- [ ] Consistent behavior across entry points
- [ ] Documentation for all settings

### 3. Remove Debug/Temporary Code (1.5 hours)
**Priority:** HIGH
**Files to review:**
- All files with "TODO", "FIXME", "HACK" comments
- Commented-out code blocks
- Debug print statements (if any remain)

**Current Problem:**
```python
# TODO: This is temporary, fix before production
# HACK: Quick workaround for demo
# import pdb; pdb.set_trace()  # DEBUG
```

**Fix Strategy:**
1. [ ] Search codebase for debug markers
2. [ ] Either fix properly or document as technical debt
3. [ ] Remove debug statements
4. [ ] Clean up commented code
5. [ ] Update documentation for intentional TODOs

**Search Commands:**
```bash
grep -r "TODO\|FIXME\|HACK\|XXX" app/ --include="*.py"
grep -r "import pdb\|breakpoint()" app/ --include="*.py"
grep -r "^#.*def \|^#.*class " app/ --include="*.py"  # Commented code
```

**Success Criteria:**
- [ ] All HACK comments resolved or documented
- [ ] No debug breakpoints in code
- [ ] Commented code removed or explained
- [ ] TODO comments have GitHub issues

## Testing Strategy

### Import Testing
```python
# test_imports.py
def test_imports_work_without_syspath():
    """Verify imports work without sys.path manipulation."""
    import subprocess
    result = subprocess.run(
        ["python", "-c", "from app.core.document_framework import DocumentGenerationFramework"],
        cwd="/tmp",  # Different directory
        capture_output=True
    )
    assert result.returncode == 0

def test_plugin_imports():
    """Verify plugin imports work correctly."""
    from app.plugins.informed_consent.plugin import InformedConsentPlugin
    from app.plugins.clinical_protocol.plugin import ClinicalProtocolPlugin
    assert InformedConsentPlugin is not None
    assert ClinicalProtocolPlugin is not None
```

### Configuration Testing
```python
def test_config_consistency():
    """Verify same config used everywhere."""
    from app.main import app as main_app
    from app.api import app as api_app

    # Both should use same CORS config
    main_cors = get_cors_config(main_app)
    api_cors = get_cors_config(api_app)
    assert main_cors == api_cors

def test_environment_override():
    """Verify environment variables work."""
    os.environ["CORS_ORIGINS"] = "http://test.com"
    from app.config import AppConfig
    assert "http://test.com" in AppConfig.CORS_ORIGINS
```

### Integration Testing
```bash
# Test from different directories
cd /tmp
python /path/to/irb-ki-summary/run_test.py --pdf /path/to/test.pdf

# Test with different environments
export CORS_ORIGINS="http://production.com"
uvicorn app.main:app

# Test package installation
pip install -e .
python -c "from app.core.document_framework import DocumentGenerationFramework"
```

## Migration Path

1. **Phase 1:** Add proper __init__.py files
2. **Phase 2:** Create AppConfig class
3. **Phase 3:** Update imports one module at a time
4. **Phase 4:** Remove sys.path manipulation
5. **Phase 5:** Test in production-like environment

## Deployment Checklist

- [ ] Works in development
- [ ] Works when installed via pip
- [ ] Works in Docker container
- [ ] Works with gunicorn/production server
- [ ] Environment variables documented
- [ ] Configuration validation passes

## References

- TECHNICAL_DEBT_ANALYSIS.md sections 2.2, 4.1, 4.2
- Python packaging best practices
- 12-factor app configuration methodology
