---
subtask: 01-quick-wins
parent: h-refactor-address-technical-debt
status: completed
estimated_hours: 2.5
completed: 2025-10-20
---

# Quick Wins - Immediate Fixes

## Goal
Address high-value, low-effort issues that provide immediate benefits with minimal risk.

## Issues to Fix

### 1. Replace Debug Print Statements (0.5 hours)
**Priority:** HIGH
**Files affected:**
- app/core/document_framework.py (line 95, 126)
- app/core/plugin_manager.py (line 45, 67)

**Current Problem:**
```python
print("DEBUG: Loading plugin...")  # Uncontrolled output
```

**Fix:**
```python
logger.debug("Loading plugin...")  # Proper log level management
```

**Success Criteria:**
- [ ] All `print()` statements replaced with `logger` calls
- [ ] Appropriate log levels used (debug, info, warning, error)
- [ ] No print statements in production code paths

### 2. Fix Bare Except Clauses (1 hour)
**Priority:** CRITICAL
**Files affected:**
- .claude/hooks/pre-tool-use.py
- .claude/hooks/post-tool-use.py
- .claude/hooks/session-start.py
- .claude/hooks/memory-capture.py
- .claude/hooks/shared_state.py
- .claude/hooks/update_memory.py
- .claude/hooks/knowledge_graph.py
- app/api.py

**Current Problem:**
```python
try:
    risky_operation()
except:  # Swallows all exceptions silently!
    pass
```

**Fix:**
```python
try:
    risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    # Decide: re-raise, return default, or handle specifically
```

**Success Criteria:**
- [ ] All bare `except:` replaced with specific exception handling
- [ ] Errors logged with context
- [ ] Appropriate error recovery strategy for each case

### 3. Remove Unused RAG References (0.5 hours)
**Priority:** MEDIUM
**Files affected:**
- Multiple files with commented RAG code
- Imports for removed RAG functionality

**Current Problem:**
- Dead code from removed RAG pipeline
- Confusing comments and imports

**Fix:**
- Remove all RAG-related comments
- Remove unused RAG imports
- Clean up commented-out RAG code

**Success Criteria:**
- [ ] No references to removed RAG functionality
- [ ] Clean import statements
- [ ] No commented-out RAG code blocks

### 4. Fix Hardcoded CORS Configuration (0.5 hours)
**Priority:** HIGH
**Files affected:**
- app/main.py:29
- app/api.py:45

**Current Problem:**
```python
# main.py
allow_origins=["http://localhost:3000"]  # Hardcoded

# api.py
allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")  # Better
```

**Fix:**
Standardize on environment-based configuration:
```python
# Both files
allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
```

**Success Criteria:**
- [ ] Consistent CORS config across main.py and api.py
- [ ] Environment variable based configuration
- [ ] Default value for development
- [ ] Documentation updated

## Testing

### Pre-Implementation Tests
- [ ] Run existing test suite to establish baseline
- [ ] Generate consistency report with 10 runs
- [ ] Document current behavior

### Post-Implementation Tests
- [ ] All existing tests pass
- [ ] Consistency report shows no regression (CV < 15%)
- [ ] Server starts without errors
- [ ] Log output is clean and informative

## Implementation Notes

### Order of Operations
1. Add proper logging infrastructure if needed
2. Replace print statements (safe, easy to verify)
3. Fix bare except clauses (test each hook individually)
4. Remove unused RAG code (search carefully)
5. Fix CORS configuration (test with frontend if available)

### Verification Commands
```bash
# Check for remaining print statements
grep -r "print(" app/ --include="*.py" | grep -v "# OK:" | grep -v ".pyc"

# Check for bare except clauses
grep -r "except:" app/ .claude/hooks/ --include="*.py"

# Check for RAG references
grep -ri "rag\|llamaindex\|vector" app/ --include="*.py"

# Test server startup
uvicorn app.main:app --reload

# Run consistency test
python run_test.py --pdf test_data/HUM00173014.pdf --repeat 10
```

## Rollback Plan

If issues arise:
1. Git checkout the specific file that caused issues
2. Each fix is independent and can be rolled back individually
3. Commits should be atomic (one fix per commit)

## References

- TECHNICAL_DEBT_ANALYSIS.md sections 1.1, 2.1, 5.1, 6.2
- Python logging documentation
- CORS configuration best practices
