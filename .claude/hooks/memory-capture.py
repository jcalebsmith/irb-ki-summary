#!/usr/bin/env python3
"""Memory capture hook for recording observations from tool use and conversations."""
import json
import sys
from pathlib import Path
from datetime import datetime
from shared_state import (
    get_project_root,
    get_task_state,
    add_memory_observation,
    add_memory_episode,
    append_memory_event
)

def capture_tool_observation(tool_name: str, file_path: str = None, operation: str = None):
    """Capture observations from tool use."""
    task_state = get_task_state()
    current_task = task_state.get("task", "unknown")
    
    # Determine what to observe based on tool and operation
    observations = []
    
    if tool_name == "Edit" and file_path:
        observations.append({
            "entity": file_path,
            "type": "codebase_artifact",
            "content": f"Modified during task '{current_task}' - {operation or 'edited'}",
            "tags": ["modified", current_task]
        })
    
    elif tool_name == "Write" and file_path:
        observations.append({
            "entity": file_path,
            "type": "codebase_artifact",
            "content": f"Created during task '{current_task}'",
            "tags": ["created", current_task]
        })
    
    elif tool_name == "Bash" and operation:
        # Capture important commands as procedural memory
        important_commands = ["pytest", "npm test", "npm run", "git", "make", "cargo", "python test"]
        if any(cmd in operation.lower() for cmd in important_commands):
            observations.append({
                "entity": "procedural_commands",
                "type": "workflow",
                "content": f"Command used: {operation}",
                "tags": ["command", current_task]
            })
    
    # Store observations
    for obs in observations:
        try:
            add_memory_observation(
                entity_key=obs["entity"],
                entity_type=obs["type"],
                observation=obs["content"],
                confidence=0.8,
                tags=obs.get("tags"),
                source=f"tool:{tool_name}"
            )
        except Exception as e:
            # Silently fail to not disrupt workflow
            pass

def capture_error_pattern(error_message: str, context: str = None):
    """Capture error patterns for future reference."""
    task_state = get_task_state()
    current_task = task_state.get("task", "unknown")
    
    # Extract key error information
    error_summary = error_message[:200] if len(error_message) > 200 else error_message
    
    try:
        add_memory_observation(
            entity_key="error_patterns",
            entity_type="bug_solution",
            observation=f"Error encountered: {error_summary}",
            confidence=0.7,
            tags=["error", current_task],
            source=f"task:{current_task}"
        )
        
        # Log to event stream
        append_memory_event("error_captured", {
            "task": current_task,
            "error": error_summary,
            "context": context
        })
    except Exception:
        pass

def extract_learnings_from_conversation(transcript: str = None):
    """Extract key learnings from conversation transcript."""
    if not transcript:
        return []
    
    learnings = []
    keywords = [
        "solution:", "fixed by", "resolved with", "the issue was",
        "learned that", "discovered", "found that", "turns out",
        "best practice", "should use", "prefer", "recommendation"
    ]
    
    lines = transcript.lower().split('\n')
    for line in lines:
        for keyword in keywords:
            if keyword in line:
                # Extract the learning (simplified extraction)
                learning = line.split(keyword)[-1].strip()[:150]
                if learning and len(learning) > 10:
                    learnings.append(learning)
                break
    
    return learnings

def capture_task_completion(task_name: str, success: bool = True, learnings: list = None):
    """Capture task completion as an episode."""
    try:
        # If no explicit learnings, try to extract from recent work
        if not learnings:
            learnings = ["Task completed successfully"]
        
        # Detect patterns from the task
        patterns = []
        if "test" in task_name.lower():
            patterns.append("test_driven_development")
        if "refactor" in task_name.lower():
            patterns.append("refactoring")
        if "fix" in task_name.lower() or "bug" in task_name.lower():
            patterns.append("bug_fixing")
        
        add_memory_episode(
            task_name=task_name,
            learnings=learnings,
            patterns=patterns,
            success=success
        )
        
        # Log completion
        append_memory_event("task_completed", {
            "task": task_name,
            "success": success,
            "learnings_count": len(learnings)
        })
    except Exception:
        pass

def capture_user_preference(preference: str, category: str = "general"):
    """Capture user preferences from interactions."""
    try:
        add_memory_observation(
            entity_key=f"user_preference_{category}",
            entity_type="user_preference",
            observation=preference,
            confidence=0.85,
            tags=[category, "preference"],
            source="user_interaction"
        )
    except Exception:
        pass

# Main hook function for post-tool-use integration
def process_tool_use(tool_data: dict):
    """Process tool use for memory capture."""
    tool_name = tool_data.get("tool_name")
    
    if tool_name == "Edit":
        file_path = tool_data.get("parameters", {}).get("file_path")
        capture_tool_observation("Edit", file_path, "modified")
    
    elif tool_name == "Write":
        file_path = tool_data.get("parameters", {}).get("file_path")
        capture_tool_observation("Write", file_path, "created")
    
    elif tool_name == "Bash":
        command = tool_data.get("parameters", {}).get("command", "")
        capture_tool_observation("Bash", operation=command)
        
        # Check for test commands to capture preferences
        if "pytest" in command.lower():
            capture_user_preference("Uses pytest for Python testing", "testing")
        elif "npm test" in command.lower():
            capture_user_preference("Uses npm test for JavaScript testing", "testing")

if __name__ == "__main__":
    # Can be called from other hooks
    import sys
    if len(sys.argv) > 1:
        tool_data = json.loads(sys.argv[1])
        process_tool_use(tool_data)