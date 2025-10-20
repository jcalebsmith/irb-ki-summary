---
subtask: 02-critical-issues
parent: h-refactor-address-technical-debt
status: pending
estimated_hours: 4.5
---

# Critical Issues - Silent Failures

## Goal
Fix silent error handling that allows failures to propagate without detection, causing cascading issues and debugging nightmares.

## Issues to Fix

### 1. Document Processor Silent Failures (2 hours)
**Priority:** CRITICAL
**File:** app/core/document_processor.py

**Current Problem:**
```python
def process_document(doc):
    try:
        result = extract_data(doc)
        if not result:
            return {}  # Silent failure - empty dict propagates
    except Exception:
        return {}  # Swallowed exception
```

**Impact:**
- Empty extraction results propagate silently
- No indication of what went wrong
- Users see incomplete/empty output without explanation
- Debugging requires code inspection

**Fix Strategy:**
```python
def process_document(doc):
    try:
        result = extract_data(doc)
        if not result:
            logger.warning("Extraction returned empty result for document")
            raise DocumentProcessingError("Failed to extract data from document")
        return result
    except ExtractorError as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        raise DocumentProcessingError(f"Document processing failed: {e}") from e
```

**Success Criteria:**
- [ ] Empty results raise appropriate exceptions
- [ ] Errors logged with full context
- [ ] User-friendly error messages in API responses
- [ ] Tests added for error cases

### 2. Unified Extractor Silent Failures (1.5 hours)
**Priority:** CRITICAL
**File:** app/plugins/informed_consent/unified_extractor.py

**Current Problem:**
```python
def extract_sections(text):
    sections = parse_sections(text)
    if not sections:
        return []  # Silent - no indication of parse failure
    return sections
```

**Impact:**
- Failed extraction returns empty list
- Template rendering receives empty data
- Generated document has missing sections
- No error reporting to user

**Fix Strategy:**
```python
def extract_sections(text):
    if not text or not text.strip():
        raise ValueError("Cannot extract sections from empty text")

    sections = parse_sections(text)
    if not sections:
        logger.error(f"Failed to parse sections from text (length: {len(text)})")
        raise ExtractionError("No sections found in document text")

    logger.info(f"Successfully extracted {len(sections)} sections")
    return sections
```

**Success Criteria:**
- [ ] Empty/invalid inputs raise ValueError
- [ ] Parse failures raise ExtractionError
- [ ] Success cases logged with metrics
- [ ] API returns descriptive error messages
- [ ] Tests for edge cases added

### 3. Error Propagation in Framework (1 hour)
**Priority:** HIGH
**File:** app/core/document_framework.py

**Current Problem:**
- Errors caught at framework level but not properly communicated
- Result objects contain error info but aren't checked consistently
- Silent degradation when plugins fail

**Fix Strategy:**
```python
# Improve result checking
result = await plugin.process(doc)
if not result.success:
    logger.error(f"Plugin {plugin_id} failed: {result.error_message}")
    raise PluginExecutionError(
        f"Failed to process document with {plugin_id}: {result.error_message}",
        details=result.metadata
    )

# Add validation after each major step
if not generated_content or len(generated_content.strip()) < 100:
    raise ValidationError("Generated content is too short or empty")
```

**Success Criteria:**
- [ ] All plugin failures raise exceptions
- [ ] Validation checks after generation
- [ ] Error context preserved through call stack
- [ ] Graceful error messages for users

## Custom Exception Classes

Create new exception hierarchy:

```python
# app/core/exceptions.py (enhance existing)

class DocumentProcessingError(DocumentFrameworkError):
    """Raised when document processing fails."""
    pass

class ExtractionError(DocumentProcessingError):
    """Raised when data extraction fails."""
    pass

class ValidationError(DocumentProcessingError):
    """Raised when validation checks fail."""
    pass

class PluginExecutionError(DocumentFrameworkError):
    """Raised when plugin execution fails."""
    pass
```

## Error Response Format

Standardize API error responses:

```python
{
    "error": "DocumentProcessingError",
    "message": "Failed to extract data from document",
    "details": {
        "document_type": "informed-consent-ki",
        "extraction_step": "section_parsing",
        "text_length": 1234
    },
    "timestamp": "2025-10-20T12:34:56Z"
}
```

## Testing Strategy

### Unit Tests
```python
def test_empty_document_raises_error():
    with pytest.raises(ValueError, match="empty text"):
        extract_sections("")

def test_failed_extraction_raises_error():
    with pytest.raises(ExtractionError):
        process_malformed_document()

def test_error_message_in_response():
    response = client.post("/generate/", data=bad_data)
    assert response.status_code == 400
    assert "error" in response.json()
    assert "details" in response.json()
```

### Integration Tests
```bash
# Test with actual PDF that should fail extraction
python run_test.py --pdf test_data/corrupted.pdf

# Should return HTTP 400 with error details, not HTTP 200 with empty content
```

## Rollback Plan

1. Keep old code commented out initially
2. Deploy with feature flag for new error handling
3. Monitor error rates and user feedback
4. Roll back if error rates spike unexpectedly

## Monitoring

Add metrics to track:
- Error types and frequencies
- Failed extractions by document type
- Average error recovery time
- User-reported issues

## References

- TECHNICAL_DEBT_ANALYSIS.md section 1.2 (Silent Failures)
- Python exception handling best practices
- API error response standards
