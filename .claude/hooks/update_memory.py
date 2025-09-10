#!/usr/bin/env python3
"""Script to update memory with learnings from task completion."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared_state import add_memory_episode, add_memory_observation
from memory_capture import extract_learnings_from_conversation

def main():
    parser = argparse.ArgumentParser(description="Update memory with task learnings")
    parser.add_argument("--task", required=True, help="Task name")
    parser.add_argument("--learnings", help="Pipe-separated learnings")
    parser.add_argument("--success", default="true", help="Task success (true/false)")
    parser.add_argument("--patterns", help="Pipe-separated patterns detected")
    parser.add_argument("--preference", help="User preference to record")
    parser.add_argument("--observation", help="Codebase observation to record")
    parser.add_argument("--entity", help="Entity key for observation")
    
    args = parser.parse_args()
    
    # Process task episode if learnings provided
    if args.learnings:
        learnings = args.learnings.split("|")
        patterns = args.patterns.split("|") if args.patterns else []
        success = args.success.lower() == "true"
        
        add_memory_episode(
            task_name=args.task,
            learnings=learnings,
            patterns=patterns,
            success=success
        )
        print(f"✓ Added episode for task '{args.task}' with {len(learnings)} learnings")
    
    # Process user preference if provided
    if args.preference:
        add_memory_observation(
            entity_key="user_preferences",
            entity_type="user_preference",
            observation=args.preference,
            confidence=0.9,
            source=f"task:{args.task}"
        )
        print(f"✓ Added user preference: {args.preference}")
    
    # Process codebase observation if provided
    if args.observation and args.entity:
        add_memory_observation(
            entity_key=args.entity,
            entity_type="codebase_artifact",
            observation=args.observation,
            confidence=0.85,
            source=f"task:{args.task}"
        )
        print(f"✓ Added observation for {args.entity}")

if __name__ == "__main__":
    main()