#!/usr/bin/env python3

import sys
import os
import json
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from knowledge_graph import KnowledgeGraph
from shared_state import SharedState

def main():
    """Initialize knowledge graph on session start"""
    try:
        # Initialize shared state
        state = SharedState()
        
        # Load or create knowledge graph
        kg = KnowledgeGraph()
        
        # Store in shared state for other hooks
        state.set("knowledge_graph", kg)
        state.set("kg_changes", 0)
        state.set("kg_modified", False)
        
        # Get graph stats
        stats = kg.metadata.get("stats", {})
        last_updated = kg.metadata.get("last_updated")
        
        # Create status message
        messages = []
        
        if stats.get("total_nodes", 0) > 0:
            messages.append(f"📊 Knowledge Graph loaded: {stats.get('total_nodes', 0)} files indexed")
            
            if last_updated:
                try:
                    last_time = datetime.fromisoformat(last_updated)
                    age = datetime.now() - last_time
                    if age > timedelta(days=7):
                        messages.append(f"⚠️  Graph is {age.days} days old - consider refreshing")
                except:
                    pass
            
            # Show some useful stats
            if stats.get("indexed_components", 0) > 0:
                messages.append(f"   • {stats.get('indexed_components', 0)} components tracked")
            if stats.get("indexed_imports", 0) > 0:
                messages.append(f"   • {stats.get('indexed_imports', 0)} import relationships")
        else:
            messages.append("📊 Knowledge Graph initialized (empty - will populate as you work)")
        
        # Get current task if any
        task_file = ".claude/state/current_task.json"
        if os.path.exists(task_file):
            try:
                with open(task_file, 'r') as f:
                    task_data = json.load(f)
                    if task_data.get("task"):
                        task_name = task_data["task"]
                        
                        # Try to get relevant context from graph
                        keywords = task_name.split('-')
                        context = kg.get_context_for_task(keywords)
                        
                        if context.get("direct_matches"):
                            messages.append(f"\n🎯 Found {len(context['direct_matches'])} relevant files for task: {task_name}")
            except:
                pass
        
        # Print messages
        if messages:
            print("\n".join(messages))
        
        # Cleanup old snapshots
        kg.cleanup_old_snapshots(keep_last=10)
        
    except Exception as e:
        # Silently fail but log for debugging
        state = SharedState()
        state.set("kg_init_error", str(e))

if __name__ == "__main__":
    main()