#!/usr/bin/env python3
"""Test script for knowledge capture functionality."""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared_state import (
    load_memory_index,
    get_contextual_memory,
    query_memory_semantic
)
# Import memory-capture module (with hyphen in filename)
import importlib.util
spec = importlib.util.spec_from_file_location("memory_capture", 
                                               Path(__file__).parent / "memory-capture.py")
memory_capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memory_capture)

capture_tool_observation = memory_capture.capture_tool_observation
capture_error_pattern = memory_capture.capture_error_pattern
capture_user_preference = memory_capture.capture_user_preference
capture_task_completion = memory_capture.capture_task_completion
extract_learnings_from_conversation = memory_capture.extract_learnings_from_conversation

def test_knowledge_capture():
    """Test the knowledge capture functionality."""
    print("Testing Knowledge Capture (Phase 2)")
    print("=" * 40)
    
    # Get initial memory state
    initial_memory = load_memory_index()
    initial_count = initial_memory['statistics']['total_observations']
    
    # Test 1: Tool observation capture
    print("\n1. Testing tool observation capture...")
    capture_tool_observation("Edit", "/test/file.py", "modified")
    capture_tool_observation("Write", "/test/new_file.js", "created")
    capture_tool_observation("Bash", operation="pytest -v tests/")
    
    memory_after_tools = load_memory_index()
    new_observations = memory_after_tools['statistics']['total_observations'] - initial_count
    print(f"✓ Captured {new_observations} tool observations")
    
    # Test 2: Error pattern capture
    print("\n2. Testing error pattern capture...")
    capture_error_pattern(
        "ImportError: No module named 'tiktoken'",
        context="During memory system testing"
    )
    print("✓ Captured error pattern")
    
    # Test 3: User preference capture
    print("\n3. Testing user preference capture...")
    capture_user_preference("Always use type hints in Python code", "coding_style")
    capture_user_preference("Prefer async/await over callbacks", "javascript")
    print("✓ Captured 2 user preferences")
    
    # Test 4: Learning extraction from conversation
    print("\n4. Testing learning extraction...")
    sample_transcript = """
    The issue was that the authentication middleware wasn't checking the cache.
    I discovered that we need to validate tokens against Redis first.
    The solution: always check the Redis cache before database validation.
    Best practice is to use a 5-minute TTL for security tokens.
    It turns out the performance issue was due to missing indexes.
    """
    learnings = extract_learnings_from_conversation(sample_transcript)
    print(f"✓ Extracted {len(learnings)} learnings from conversation")
    for i, learning in enumerate(learnings[:3], 1):
        print(f"  {i}. {learning[:60]}...")
    
    # Test 5: Task completion capture
    print("\n5. Testing task completion capture...")
    capture_task_completion(
        task_name="test-memory-system",
        success=True,
        learnings=[
            "Memory persistence works correctly with JSON storage",
            "Hooks integration provides seamless context capture",
            "Temporal decay helps maintain relevance"
        ]
    )
    print("✓ Captured task completion episode")
    
    # Test 6: Contextual memory retrieval
    print("\n6. Testing contextual memory retrieval...")
    context = get_contextual_memory(
        task_name="test-memory-system",
        affected_files=["/test/file.py"]
    )
    print(f"✓ Retrieved contextual memory:")
    print(f"  - User preferences: {len(context['user_preferences'])}")
    print(f"  - Recent episodes: {len(context['recent_episodes'])}")
    print(f"  - Relevant entities: {len(context['relevant_entities'])}")
    
    # Test 7: Semantic query with captured data
    print("\n7. Testing semantic query on captured data...")
    results = query_memory_semantic("pytest")
    print(f"✓ Query 'pytest' returned {len(results)} results")
    
    results = query_memory_semantic("error")
    print(f"✓ Query 'error' returned {len(results)} results")
    
    # Test 8: Verify persistence to files
    print("\n8. Verifying file persistence...")
    memory_index = Path(".claude/state/memory/memory-index.json")
    memory_events = Path(".claude/state/memory/memory.jsonl")
    
    if memory_index.exists():
        with open(memory_index) as f:
            index_data = json.load(f)
        print(f"✓ Memory index contains {len(index_data['entities'])} entities")
    
    if memory_events.exists():
        with open(memory_events) as f:
            event_count = len(f.readlines())
        print(f"✓ Memory event log contains {event_count} events")
    
    # Final statistics
    print("\n" + "=" * 40)
    final_memory = load_memory_index()
    print("✅ Knowledge capture tests completed!")
    print(f"\nFinal Statistics:")
    print(f"  • Total Entities: {final_memory['statistics']['total_entities']}")
    print(f"  • Total Observations: {final_memory['statistics']['total_observations']}")
    print(f"  • Total Episodes: {final_memory['statistics']['total_episodes']}")
    print(f"  • New observations added: {final_memory['statistics']['total_observations'] - initial_count}")

if __name__ == "__main__":
    test_knowledge_capture()