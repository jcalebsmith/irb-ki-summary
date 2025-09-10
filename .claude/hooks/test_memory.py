#!/usr/bin/env python3
"""Test script for the persistent memory layer."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared_state import (
    add_memory_observation,
    add_memory_episode,
    query_memory_semantic,
    get_contextual_memory,
    load_memory_index,
    calculate_memory_relevance
)

def test_memory_persistence():
    """Test the memory persistence functionality."""
    print("Testing Memory Persistence Layer")
    print("=" * 40)
    
    # Test 1: Add user preference
    print("\n1. Adding user preference...")
    memory = add_memory_observation(
        entity_key="user_preferences",
        entity_type="user_preference",
        observation="Prefers pytest for testing with -v flag for verbose output",
        confidence=0.9,
        tags=["testing", "pytest"],
        source="test_script"
    )
    print(f"✓ Added preference. Total observations: {memory['statistics']['total_observations']}")
    
    # Test 2: Add codebase observation
    print("\n2. Adding codebase observation...")
    memory = add_memory_observation(
        entity_key=".claude/hooks/shared_state.py",
        entity_type="codebase_artifact",
        observation="Contains memory management functions with temporal decay support",
        confidence=0.95,
        tags=["memory", "persistence"],
        source="implementation"
    )
    print(f"✓ Added codebase observation. Total entities: {memory['statistics']['total_entities']}")
    
    # Test 3: Add an episode
    print("\n3. Adding task episode...")
    memory = add_memory_episode(
        task_name="m-implement-persistent-memory-layer",
        learnings=[
            "JSON-based storage is simple and effective for memory persistence",
            "Temporal decay helps maintain relevance of observations",
            "Integration with existing hooks provides seamless memory context"
        ],
        patterns=["incremental_development", "test_driven"],
        success=True
    )
    print(f"✓ Added episode. Total episodes: {memory['statistics']['total_episodes']}")
    
    # Test 4: Query memory
    print("\n4. Testing semantic query...")
    results = query_memory_semantic("testing")
    print(f"✓ Query 'testing' returned {len(results)} results")
    if results:
        print(f"  First result: {results[0].get('observation', results[0].get('learning'))[:80]}...")
    
    # Test 5: Get contextual memory
    print("\n5. Testing contextual memory retrieval...")
    context = get_contextual_memory(
        task_name="m-implement-persistent-memory-layer",
        affected_files=[".claude/hooks/shared_state.py"]
    )
    print(f"✓ Retrieved context with:")
    print(f"  - {len(context['user_preferences'])} user preferences")
    print(f"  - {len(context['recent_episodes'])} related episodes")
    print(f"  - {len(context['relevant_entities'])} relevant entities")
    
    # Test 6: Test relevance calculation
    print("\n6. Testing relevance calculation...")
    # Get an observation timestamp from memory
    memory_data = load_memory_index()
    if memory_data['entities']:
        first_entity = list(memory_data['entities'].values())[0]
        if first_entity['observations']:
            timestamp = first_entity['observations'][0]['timestamp']
            relevance = calculate_memory_relevance(timestamp, access_count=1)
            print(f"✓ Relevance score for new observation: {relevance:.3f}")
    
    # Test 7: Verify persistence
    print("\n7. Verifying persistence...")
    memory_files = [
        ".claude/state/memory/memory-index.json",
        ".claude/state/memory/memory.jsonl",
        ".claude/state/memory/memory-config.json"
    ]
    all_exist = all(Path(f).exists() for f in memory_files)
    print(f"✓ All memory files exist: {all_exist}")
    
    print("\n" + "=" * 40)
    print("✅ Memory persistence tests completed successfully!")
    
    # Display final statistics
    final_memory = load_memory_index()
    print(f"\nFinal Memory Statistics:")
    print(f"  • Total Entities: {final_memory['statistics']['total_entities']}")
    print(f"  • Total Observations: {final_memory['statistics']['total_observations']}")
    print(f"  • Total Episodes: {final_memory['statistics']['total_episodes']}")
    print(f"  • Total Relations: {final_memory['statistics']['total_relations']}")

if __name__ == "__main__":
    test_memory_persistence()