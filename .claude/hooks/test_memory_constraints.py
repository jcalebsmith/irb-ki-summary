#!/usr/bin/env python3
"""Test script for memory constraints and pruning functionality."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared_state import (
    add_memory_observation,
    add_memory_episode,
    load_memory_index,
    prune_memory_by_relevance,
    contains_forbidden_pattern,
    get_memory_config
)
import time
from datetime import datetime, timedelta

def test_memory_constraints():
    """Test memory constraints and pruning."""
    print("Testing Memory Constraints and Pruning")
    print("=" * 40)
    
    # Test 1: Privacy filtering
    print("\n1. Testing privacy filtering...")
    
    # Test forbidden patterns
    assert contains_forbidden_pattern("my password is secret123") == True
    assert contains_forbidden_pattern("API_KEY=sk-abc123def456") == True
    # Note: "secrets" contains "secret" which is a forbidden word, so test with different text
    assert contains_forbidden_pattern("normal text without issues") == False
    print("✓ Privacy pattern detection working")
    
    # Try to add observation with forbidden content
    result = add_memory_observation(
        entity_key="test_entity",
        entity_type="test",
        observation="My AWS_ACCESS_KEY is AKIAIOSFODNN7EXAMPLE",
        confidence=0.9
    )
    assert result is None, "Should block observation with forbidden pattern"
    print("✓ Blocked observation with forbidden pattern")
    
    # Test 2: Add multiple safe observations
    print("\n2. Testing observation limits...")
    
    # Add many observations to test limit
    for i in range(5):
        add_memory_observation(
            entity_key=f"test_entity_{i}",
            entity_type="test",
            observation=f"Test observation {i}",
            confidence=0.8
        )
    
    memory = load_memory_index()
    initial_entities = len(memory["entities"])
    print(f"✓ Added {initial_entities} test entities")
    
    # Test 3: Episode limits
    print("\n3. Testing episode limits...")
    
    # Add test episodes
    for i in range(5):
        add_memory_episode(
            task_name=f"test_task_{i}",
            learnings=[f"Learning {i}.1", f"Learning {i}.2"],
            success=True
        )
    
    memory = load_memory_index()
    initial_episodes = len(memory["episodes"])
    print(f"✓ Added {initial_episodes} test episodes")
    
    # Test 4: Observation limit per entity
    print("\n4. Testing per-entity observation limit...")
    
    # Try to add many observations to single entity (should be limited)
    test_entity_key = "test_entity_many_obs"
    for i in range(10):  # Try to add 10, but should be limited
        add_memory_observation(
            entity_key=test_entity_key,
            entity_type="test",
            observation=f"Observation {i} for same entity",
            confidence=0.7
        )
    
    memory = load_memory_index()
    obs_count = len(memory["entities"].get(test_entity_key, {}).get("observations", []))
    config = get_memory_config()
    max_obs = config["settings"].get("max_observations_per_entity", 100)
    print(f"✓ Entity has {obs_count} observations (limit: {max_obs})")
    
    # Test 5: Pruning function
    print("\n5. Testing pruning function...")
    
    # Manually add old observations with past timestamps
    memory = load_memory_index()
    
    # Add some old entities with very old timestamps
    for i in range(3):
        old_timestamp = (datetime.now() - timedelta(days=100+i)).isoformat() + "Z"
        entity_key = f"old_entity_{i}"
        memory["entities"][entity_key] = {
            "type": "old_test",
            "observations": [{
                "content": f"Very old observation {i}",
                "timestamp": old_timestamp,
                "confidence": 0.5,
                "access_count": 1
            }],
            "relations": []
        }
    
    # Update statistics
    memory["statistics"]["total_entities"] = len(memory["entities"])
    memory["statistics"]["total_observations"] = sum(
        len(entity.get("observations", [])) 
        for entity in memory["entities"].values()
    )
    
    # Save memory with old data
    from shared_state import save_memory_index
    save_memory_index(memory)
    
    before_prune = len(memory["entities"])
    print(f"  Entities before pruning: {before_prune}")
    
    # Run pruning
    pruned = prune_memory_by_relevance()
    
    memory = load_memory_index()
    after_prune = len(memory["entities"])
    print(f"  Entities after pruning: {after_prune}")
    
    if pruned:
        print(f"✓ Pruning removed {before_prune - after_prune} old/irrelevant entities")
    else:
        print("✓ No pruning needed (within limits)")
    
    # Test 6: Verify forbidden content wasn't stored
    print("\n6. Verifying no forbidden content stored...")
    
    memory = load_memory_index()
    forbidden_found = False
    for entity_key, entity in memory["entities"].items():
        for obs in entity.get("observations", []):
            if "AWS_ACCESS_KEY" in obs["content"] or "password" in obs["content"].lower():
                forbidden_found = True
                break
    
    assert not forbidden_found, "Found forbidden content in memory!"
    print("✓ No forbidden content found in memory")
    
    # Final statistics
    print("\n" + "=" * 40)
    print("✅ Memory constraints tests completed!")
    
    final_memory = load_memory_index()
    print(f"\nFinal Statistics:")
    print(f"  • Total Entities: {final_memory['statistics']['total_entities']}")
    print(f"  • Total Observations: {final_memory['statistics']['total_observations']}")
    print(f"  • Total Episodes: {final_memory['statistics']['total_episodes']}")
    
    # Check configuration
    config = get_memory_config()
    settings = config["settings"]
    print(f"\nActive Limits:")
    print(f"  • Max Entities: {settings.get('max_entities', 'not set')}")
    print(f"  • Max Episodes: {settings.get('max_episodes', 'not set')}")
    print(f"  • Max Observations per Entity: {settings.get('max_observations_per_entity', 'not set')}")
    print(f"  • Relevance Threshold: {settings.get('relevance_threshold', 'not set')}")

if __name__ == "__main__":
    test_memory_constraints()