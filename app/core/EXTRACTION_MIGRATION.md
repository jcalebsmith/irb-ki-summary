# Extraction Pipeline Migration Guide

## Overview
We have consolidated 7 different extraction implementations into a single `UnifiedExtractor` class.
This reduces code from ~2,333 lines to ~250 lines while maintaining all functionality.

## Deprecated Modules
The following modules are now DEPRECATED and will be removed:
- `evidence_pipeline.py` (935 lines) → Use `UnifiedExtractor`
- `evidence_extraction_agent.py` (496 lines) → Use `UnifiedExtractor`
- `simple_extraction.py` (167 lines) → Use `UnifiedExtractor`
- Parts of `llm_integration.py` → Extract methods moved to `UnifiedExtractor`
- Parts of `semantic_validation.py` → Self-healing extraction moved to `UnifiedExtractor`
- Parts of `llm_validation.py` → LLM extraction moved to `UnifiedExtractor`

## Migration Examples

### Before: Using EvidenceGatheringPipeline
```python
from app.core.evidence_pipeline import EvidenceGatheringPipeline

pipeline = EvidenceGatheringPipeline(llm=llm_client)
evidence = await pipeline.gather_evidence(document, field_spec)
value = await pipeline.infer_value_from_evidence(evidence, field_spec)
```

### After: Using UnifiedExtractor
```python
from app.core.unified_extractor import UnifiedExtractor

extractor = UnifiedExtractor(llm_client)
result = await extractor.extract(
    document=document,
    extraction_type="evidence",
    field_specs={"field_name": field_spec}
)
value = result["field_name"].value
```

### Before: Using GenericLLMExtractor
```python
from app.core.llm_integration import GenericLLMExtractor

extractor = GenericLLMExtractor()
result = await extractor.extract_structured(document, OutputSchema)
```

### After: Using UnifiedExtractor
```python
from app.core.unified_extractor import UnifiedExtractor

extractor = UnifiedExtractor()
result = await extractor.extract(
    document=document,
    output_schema=OutputSchema,
    extraction_type="structured"
)
```

### Before: Using SimpleChainOfThoughtExtractor
```python
from app.core.simple_extraction import SimpleChainOfThoughtExtractor

extractor = SimpleChainOfThoughtExtractor()
result = await extractor.extract(document, field_specs)
```

### After: Using UnifiedExtractor
```python
from app.core.unified_extractor import UnifiedExtractor

extractor = UnifiedExtractor()
result = await extractor.extract(
    document=document,
    extraction_type="simple",
    field_specs=field_specs
)
```

## Key Benefits

### 1. Simplified API
- Single `extract()` method for all extraction types
- Consistent return types
- Clear extraction type parameter

### 2. Reduced Complexity
- 250 lines vs 2,333 lines
- Single class vs 7 classes
- Clear, maintainable code

### 3. Better Testing
- Single module to test
- Consistent behavior
- Easier to mock

### 4. Performance
- Reduced memory footprint
- Faster imports
- Less overhead

## Removal Timeline
1. **Phase 1 (Now)**: UnifiedExtractor available, old modules deprecated
2. **Phase 2**: Update all integration points to use UnifiedExtractor
3. **Phase 3**: Remove deprecated modules

## Integration Points to Update
- [x] `multi_agent_system.py` - ExtractionAgent updated
- [ ] `document_framework.py` - Update to use UnifiedExtractor
- [ ] Plugin implementations - Update extraction calls
- [ ] Tests - Create new tests for UnifiedExtractor