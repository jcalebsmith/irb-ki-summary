---
subtask: 03-llm-integration-cleanup
parent: h-refactor-app-comprehensive-cleanup
status: pending
---

# LLM Integration Cleanup

## Objective
Update LLM integration to use latest OpenAI SDK patterns and remove custom implementations where framework solutions exist.

## Scope
- app/core/llm_integration.py
- app/core/llm_validation.py
- All files using OpenAI SDK

## OpenAI SDK Best Practices (via context7)
- [ ] Verify latest SDK version and patterns
- [ ] Check structured output usage
- [ ] Review retry and error handling patterns
- [ ] Validate token counting methods
- [ ] Check streaming implementation
- [ ] Review function calling patterns

## Refactoring Tasks
- [ ] Update to latest OpenAI Python SDK patterns
- [ ] Replace custom retry logic with SDK built-ins
- [ ] Use official structured output features
- [ ] Implement proper async/await patterns
- [ ] Remove deprecated API usage
- [ ] Consolidate LLM configuration

## Code Improvements
- [ ] Remove custom token counting if SDK provides it
- [ ] Use SDK's built-in error types
- [ ] Implement proper connection pooling
- [ ] Add request/response logging
- [ ] Implement cost tracking
- [ ] Add proper timeout handling

## Integration Testing
- [ ] Create tests with real OpenAI API calls
- [ ] Test structured output parsing
- [ ] Verify error handling with real errors
- [ ] Test rate limiting behavior
- [ ] Validate streaming responses
- [ ] Test function calling end-to-end

## Success Criteria
- [ ] All LLM calls use latest SDK patterns
- [ ] No custom code where SDK features exist
- [ ] Real API integration tests passing
- [ ] Proper error handling and logging
- [ ] Cost tracking implemented
- [ ] Response times optimized