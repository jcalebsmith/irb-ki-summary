---
subtask: 05-long-term
parent: h-refactor-address-technical-debt
status: pending
estimated_hours: 8
---

# Long-Term Improvements - Performance & Infrastructure

## Goal
Address performance concerns and establish infrastructure for long-term maintainability and scalability.

## Performance Optimizations

### 1. LLM Response Caching (3 hours)
**Priority:** LOW
**Impact:** Reduce API costs and response times

**Current Problem:**
- Same PDF processed multiple times generates identical LLM calls
- No caching of LLM responses
- Expensive repeated API calls

**Solution:**

```python
# app/core/llm_cache.py
import hashlib
import json
from typing import Optional
import redis

class LLMCache:
    """Cache LLM responses to reduce API calls."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis = redis.from_url(redis_url) if redis_url else None
        self.local_cache = {}

    def _get_cache_key(self, prompt: str, model: str, temperature: float) -> str:
        """Generate cache key from request parameters."""
        key_data = f"{prompt}:{model}:{temperature}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, prompt: str, model: str, temperature: float) -> Optional[str]:
        """Get cached response if available."""
        key = self._get_cache_key(prompt, model, temperature)

        # Try Redis first
        if self.redis:
            cached = self.redis.get(key)
            if cached:
                return json.loads(cached)

        # Fall back to local cache
        return self.local_cache.get(key)

    def set(self, prompt: str, model: str, temperature: float, response: str, ttl: int = 3600):
        """Cache LLM response."""
        key = self._get_cache_key(prompt, model, temperature)

        if self.redis:
            self.redis.setex(key, ttl, json.dumps(response))
        else:
            self.local_cache[key] = response
```

**Configuration:**
```python
# app/config.py
CACHE_ENABLED = os.getenv("LLM_CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL = int(os.getenv("LLM_CACHE_TTL", "3600"))  # 1 hour
REDIS_URL = os.getenv("REDIS_URL", None)  # Optional Redis
```

**Success Criteria:**
- [ ] Cache hit rate tracked
- [ ] API call reduction measured
- [ ] Response time improvement verified
- [ ] Cache invalidation strategy documented

### 2. Batch Processing Support (2 hours)
**Priority:** LOW
**Impact:** Process multiple documents efficiently

**Current Problem:**
- Only single document processing
- No bulk upload support
- Inefficient for batch jobs

**Solution:**

```python
@app.post("/generate/batch/")
async def generate_batch(
    files: List[UploadFile],
    plugin_id: str = Form(...),
    parameters: Optional[str] = Form("{}")
):
    """
    Process multiple documents in batch.

    Returns job ID for tracking progress.
    """
    job_id = str(uuid.uuid4())

    # Queue documents for processing
    for file in files:
        await queue.enqueue(
            process_document_task,
            job_id=job_id,
            file_data=await file.read(),
            plugin_id=plugin_id,
            parameters=parameters
        )

    return {
        "job_id": job_id,
        "status": "queued",
        "total_documents": len(files)
    }

@app.get("/jobs/{job_id}/status/")
async def get_job_status(job_id: str):
    """Get batch job status."""
    return await queue.get_job_status(job_id)
```

**Success Criteria:**
- [ ] Batch endpoint accepts multiple files
- [ ] Job queue for async processing
- [ ] Progress tracking endpoint
- [ ] Results retrieval endpoint

### 3. Performance Monitoring (2 hours)
**Priority:** LOW
**Impact:** Identify bottlenecks proactively

**Solution:**

```python
# app/core/monitoring.py
import time
from functools import wraps
from typing import Callable

class PerformanceMonitor:
    """Track performance metrics."""

    def __init__(self):
        self.metrics = {
            "request_count": 0,
            "error_count": 0,
            "avg_response_time": 0,
            "llm_call_count": 0,
            "cache_hit_rate": 0
        }

    def track_time(self, operation: str) -> Callable:
        """Decorator to track operation timing."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start
                    self._record_success(operation, duration)
                    return result
                except Exception as e:
                    duration = time.time() - start
                    self._record_error(operation, duration, e)
                    raise
            return wrapper
        return decorator

    def get_metrics(self) -> dict:
        """Get current metrics snapshot."""
        return self.metrics.copy()

# Usage
monitor = PerformanceMonitor()

@monitor.track_time("document_generation")
async def generate_document(...):
    ...
```

**Metrics Dashboard:**
```python
@app.get("/metrics/")
async def get_metrics():
    """Get performance metrics."""
    return {
        "system": {
            "uptime": get_uptime(),
            "memory_usage": get_memory_usage(),
            "cpu_usage": get_cpu_usage()
        },
        "application": monitor.get_metrics(),
        "timestamp": datetime.utcnow().isoformat()
    }
```

**Success Criteria:**
- [ ] Request timing tracked
- [ ] Error rates monitored
- [ ] Resource usage tracked
- [ ] Metrics endpoint exposed
- [ ] Dashboard visualization (optional)

## Infrastructure Improvements

### 4. Dependency Injection (1 hour)
**Priority:** LOW
**Impact:** Better testability and modularity

**Current Problem:**
```python
# Hard to test - creates dependencies internally
class DocumentFramework:
    def __init__(self):
        self.llm = SimpleLLMClient()  # Hard-coded dependency
        self.validator = ValidationOrchestrator()
```

**Solution:**
```python
# Easy to test - dependencies injected
class DocumentFramework:
    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        validator: Optional[Validator] = None
    ):
        self.llm = llm or SimpleLLMClient()
        self.validator = validator or ValidationOrchestrator()

# In tests
def test_framework_with_mock():
    mock_llm = Mock(spec=LLMClient)
    framework = DocumentFramework(llm=mock_llm)
    # Test with controlled mock
```

**Success Criteria:**
- [ ] Core components accept injected dependencies
- [ ] Default implementations provided
- [ ] Tests use mock dependencies
- [ ] Configuration-driven initialization

## Logging & Monitoring

### 5. Structured Logging (Covered in Phase 1)
Already addressed by replacing print statements with logger calls.

### 6. Health Check Endpoint (0.5 hours)
```python
@app.get("/health/")
async def health_check():
    """
    Comprehensive health check.

    Returns system status and component health.
    """
    return {
        "status": "healthy",
        "components": {
            "database": await check_database(),
            "llm_api": await check_llm_api(),
            "cache": await check_cache()
        },
        "timestamp": datetime.utcnow().isoformat()
    }
```

## Deployment Infrastructure

### 7. Docker Optimization (Optional)
```dockerfile
# Multi-stage build for smaller images
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY app/ app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Testing Strategy

### Performance Tests
```python
def test_response_time():
    """Verify response time meets SLA."""
    start = time.time()
    response = client.post("/generate/", data=test_data)
    duration = time.time() - start
    assert duration < 10.0  # Max 10 seconds

def test_cache_effectiveness():
    """Verify cache reduces response time."""
    # First call (cache miss)
    time1 = time_request()

    # Second call (cache hit)
    time2 = time_request()

    assert time2 < time1 * 0.5  # 50% faster
```

### Load Tests
```python
# Using locust
from locust import HttpUser, task, between

class DocumentGenerationUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def generate_document(self):
        self.client.post(
            "/generate/",
            files={"file": open("test.pdf", "rb")},
            data={"plugin_id": "informed-consent-ki"}
        )
```

## Monitoring Tools

Consider integrating:
- **Prometheus** - Metrics collection
- **Grafana** - Visualization
- **Sentry** - Error tracking
- **ELK Stack** - Log aggregation

## References

- TECHNICAL_DEBT_ANALYSIS.md sections 7.1-7.3, 9.1, 10.1
- FastAPI performance best practices
- Python async performance patterns
- Monitoring and observability guides
