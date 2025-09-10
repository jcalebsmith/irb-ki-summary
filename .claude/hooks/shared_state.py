#!/usr/bin/env python3
"""Shared state management for Claude Code Sessions hooks."""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add app directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'app'))

# Get project root dynamically
def get_project_root():
    """Find project root by looking for .claude directory."""
    current = Path.cwd()
    while current.parent != current:
        if (current / ".claude").exists():
            return current
        current = current.parent
    # Fallback to current directory if no .claude found
    return Path.cwd()

PROJECT_ROOT = get_project_root()

# All state files in .claude/state/
STATE_DIR = PROJECT_ROOT / ".claude" / "state"
DAIC_STATE_FILE = STATE_DIR / "daic-mode.json"
TASK_STATE_FILE = STATE_DIR / "current_task.json"

# Mode description strings
DISCUSSION_MODE_MSG = "You are now in Discussion Mode and should focus on discussing and investigating with the user (no edit-based tools)"
IMPLEMENTATION_MODE_MSG = "You are now in Implementation Mode and may use tools to execute the agreed upon actions - when you are done return immediately to Discussion Mode"

def ensure_state_dir():
    """Ensure the state directory exists."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)

def check_daic_mode_bool() -> bool:
    """Check if DAIC (discussion) mode is enabled. Returns True for discussion, False for implementation."""
    ensure_state_dir()
    try:
        with open(DAIC_STATE_FILE, 'r') as f:
            data = json.load(f)
            return data.get("mode", "discussion") == "discussion"
    except (FileNotFoundError, json.JSONDecodeError):
        # Default to discussion mode if file doesn't exist
        set_daic_mode(True)
        return True

def check_daic_mode() -> str:
    """Check if DAIC (discussion) mode is enabled. Returns mode message."""
    ensure_state_dir()
    try:
        with open(DAIC_STATE_FILE, 'r') as f:
            data = json.load(f)
            mode = data.get("mode", "discussion")
            return DISCUSSION_MODE_MSG if mode == "discussion" else IMPLEMENTATION_MODE_MSG
    except (FileNotFoundError, json.JSONDecodeError):
        # Default to discussion mode if file doesn't exist
        set_daic_mode(True)
        return DISCUSSION_MODE_MSG

def toggle_daic_mode() -> str:
    """Toggle DAIC mode and return the new state message."""
    ensure_state_dir()
    # Read current mode
    try:
        with open(DAIC_STATE_FILE, 'r') as f:
            data = json.load(f)
            current_mode = data.get("mode", "discussion")
    except (FileNotFoundError, json.JSONDecodeError):
        current_mode = "discussion"
    
    # Toggle and write new value
    new_mode = "implementation" if current_mode == "discussion" else "discussion"
    with open(DAIC_STATE_FILE, 'w') as f:
        json.dump({"mode": new_mode}, f, indent=2)
    
    # Return appropriate message
    return IMPLEMENTATION_MODE_MSG if new_mode == "implementation" else DISCUSSION_MODE_MSG

def set_daic_mode(value: str|bool):
    """Set DAIC mode to a specific value."""
    ensure_state_dir()
    if value == True or value == "discussion":
        mode = "discussion"
        name = "Discussion Mode"
    elif value == False or value == "implementation":
        mode = "implementation"
        name = "Implementation Mode"
    else:
        raise ValueError(f"Invalid mode value: {value}")
    
    with open(DAIC_STATE_FILE, 'w') as f:
        json.dump({"mode": mode}, f, indent=2)
    return name

# Task and branch state management
def get_task_state() -> dict:
    """Get current task state including branch and affected services."""
    try:
        with open(TASK_STATE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"task": None, "branch": None, "services": [], "updated": None}

def set_task_state(task: str, branch: str, services: list):
    """Set current task state."""
    state = {
        "task": task,
        "branch": branch,
        "services": services,
        "updated": datetime.now().strftime("%Y-%m-%d")
    }
    ensure_state_dir()
    with open(TASK_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    return state

def add_service_to_task(service: str):
    """Add a service to the current task's affected services list."""
    state = get_task_state()
    if service not in state.get("services", []):
        state["services"].append(service)
        ensure_state_dir()
        with open(TASK_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    return state

# Memory layer management
MEMORY_DIR = STATE_DIR / "memory"
MEMORY_INDEX_FILE = MEMORY_DIR / "memory-index.json"
MEMORY_CONFIG_FILE = MEMORY_DIR / "memory-config.json"
MEMORY_EVENTS_FILE = MEMORY_DIR / "memory.jsonl"
MEMORY_WORK_FILE = MEMORY_DIR / "memory-work.jsonl"

def ensure_memory_dir():
    """Ensure the memory directory exists."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

def get_memory_config() -> dict:
    """Load memory configuration."""
    ensure_memory_dir()
    try:
        with open(MEMORY_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Try to import config from app/config.py
        try:
            from config import MEMORY_CONFIG
            settings = MEMORY_CONFIG.copy()
        except ImportError:
            # Fallback to defaults if config not available
            settings = {
                "decay_lambda": 0.1,
                "decay_enabled": True,
                "confidence_threshold": 0.5,
                "relevance_threshold": 0.3,
                "max_entities": 5000,
                "max_episodes": 1000,
                "max_observations_per_entity": 100,
                "max_memory_size_mb": 10
            }
        
        # Return default config if file doesn't exist
        return {
            "version": "1.0.0",
            "settings": settings,
            "privacy": {
                "forbidden_patterns": [
                    "password", "api_key", "secret", "token", "credential",
                    "AWS_", "OPENAI_", "ANTHROPIC_", "GITHUB_TOKEN"
                ]
            }
        }

def load_memory_index() -> dict:
    """Load the current memory index snapshot."""
    ensure_memory_dir()
    try:
        with open(MEMORY_INDEX_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Return empty memory structure if file doesn't exist
        return {
            "version": "1.0.0",
            "updated": datetime.now().isoformat() + "Z",
            "entities": {},
            "relations": {},
            "episodes": [],
            "statistics": {
                "total_entities": 0,
                "total_relations": 0,
                "total_episodes": 0,
                "total_observations": 0
            }
        }

def save_memory_index(memory_data: dict):
    """Save the memory index snapshot."""
    ensure_memory_dir()
    memory_data["updated"] = datetime.now().isoformat() + "Z"
    with open(MEMORY_INDEX_FILE, 'w') as f:
        json.dump(memory_data, f, indent=2)

def append_memory_event(event_type: str, data: dict):
    """Append an event to the memory event log."""
    ensure_memory_dir()
    event = {
        "type": event_type,
        "timestamp": datetime.now().isoformat() + "Z",
        "data": data
    }
    with open(MEMORY_EVENTS_FILE, 'a') as f:
        f.write(json.dumps(event) + "\n")

def contains_forbidden_pattern(content: str) -> bool:
    """Check if content contains forbidden patterns for privacy."""
    config = get_memory_config()
    forbidden = config.get("privacy", {}).get("forbidden_patterns", [])
    content_lower = content.lower()
    
    for pattern in forbidden:
        if pattern.lower() in content_lower:
            return True
    
    # Check for common credential patterns
    import re
    credential_patterns = [
        r'AKIA[0-9A-Z]{16}',  # AWS access keys start with AKIA
        r'sk-[a-zA-Z0-9]{48}',  # OpenAI keys
        r'ghp_[a-zA-Z0-9]{36}',  # GitHub tokens
        r'api[-_]?key[-_]?[=:]\s*[a-zA-Z0-9]{32,}',  # Generic API keys with assignment
    ]
    
    for pattern in credential_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return True
    
    return False

def prune_memory_by_relevance():
    """Prune memory based on relevance scores and limits."""
    memory = load_memory_index()
    config = get_memory_config()
    settings = config.get("settings", {})
    
    max_entities = settings.get("max_entities", 5000)
    max_episodes = settings.get("max_episodes", 1000)
    max_obs_per_entity = settings.get("max_observations_per_entity", 100)
    relevance_threshold = settings.get("relevance_threshold", 0.3)
    
    pruned = False
    
    # Prune old episodes if over limit
    if len(memory["episodes"]) > max_episodes:
        # Calculate relevance for each episode
        episodes_with_relevance = []
        for episode in memory["episodes"]:
            relevance = calculate_memory_relevance(episode["timestamp"])
            episodes_with_relevance.append((relevance, episode))
        
        # Sort by relevance (highest first) and keep top max_episodes
        episodes_with_relevance.sort(key=lambda x: x[0], reverse=True)
        memory["episodes"] = [ep for _, ep in episodes_with_relevance[:max_episodes]]
        pruned = True
    
    # Prune entities if over limit
    if len(memory["entities"]) > max_entities:
        # Calculate average relevance for each entity
        entities_with_relevance = []
        for key, entity in memory["entities"].items():
            total_relevance = 0
            for obs in entity.get("observations", []):
                total_relevance += calculate_memory_relevance(
                    obs["timestamp"], 
                    obs.get("access_count", 1)
                )
            avg_relevance = total_relevance / max(1, len(entity.get("observations", [])))
            entities_with_relevance.append((avg_relevance, key, entity))
        
        # Sort by relevance and keep top max_entities
        entities_with_relevance.sort(key=lambda x: x[0], reverse=True)
        memory["entities"] = {
            key: entity 
            for _, key, entity in entities_with_relevance[:max_entities]
        }
        pruned = True
    
    # Prune observations within entities
    for entity_key, entity in memory["entities"].items():
        observations = entity.get("observations", [])
        if len(observations) > max_obs_per_entity:
            # Calculate relevance for each observation
            obs_with_relevance = []
            for obs in observations:
                relevance = calculate_memory_relevance(
                    obs["timestamp"],
                    obs.get("access_count", 1)
                )
                obs_with_relevance.append((relevance, obs))
            
            # Sort by relevance and keep top max_obs_per_entity
            obs_with_relevance.sort(key=lambda x: x[0], reverse=True)
            entity["observations"] = [
                obs for _, obs in obs_with_relevance[:max_obs_per_entity]
            ]
            pruned = True
    
    # Remove entities with no observations above threshold
    entities_to_remove = []
    for key, entity in memory["entities"].items():
        observations = entity.get("observations", [])
        if observations:
            # Check if all observations are below relevance threshold
            all_below = all(
                calculate_memory_relevance(obs["timestamp"], obs.get("access_count", 1)) < relevance_threshold
                for obs in observations
            )
            if all_below:
                entities_to_remove.append(key)
    
    for key in entities_to_remove:
        del memory["entities"][key]
        pruned = True
    
    if pruned:
        # Update statistics
        memory["statistics"]["total_entities"] = len(memory["entities"])
        memory["statistics"]["total_episodes"] = len(memory["episodes"])
        memory["statistics"]["total_observations"] = sum(
            len(entity.get("observations", [])) 
            for entity in memory["entities"].values()
        )
        memory["statistics"]["last_cleanup"] = datetime.now().isoformat() + "Z"
        
        # Save pruned memory
        save_memory_index(memory)
        
        # Log pruning event
        append_memory_event("memory_pruned", {
            "entities_removed": len(entities_to_remove),
            "final_entity_count": memory["statistics"]["total_entities"],
            "final_episode_count": memory["statistics"]["total_episodes"]
        })
    
    return pruned

def add_memory_observation(entity_key: str, entity_type: str, observation: str, 
                          confidence: float = 0.8, tags: list = None, source: str = None):
    """Add an observation about an entity to memory."""
    # Privacy check - don't store if contains forbidden patterns
    if contains_forbidden_pattern(observation) or contains_forbidden_pattern(entity_key):
        append_memory_event("observation_blocked", {
            "reason": "forbidden_pattern_detected",
            "entity_type": entity_type
        })
        return None
    
    # Validate confidence range
    confidence = max(0.0, min(1.0, confidence))
    
    memory = load_memory_index()
    config = get_memory_config()
    settings = config.get("settings", {})
    
    # Check if we're at entity limit and need to prune
    max_entities = settings.get("max_entities", 5000)
    if len(memory["entities"]) >= max_entities and entity_key not in memory["entities"]:
        # Prune before adding new entity
        prune_memory_by_relevance()
        memory = load_memory_index()  # Reload after pruning
    
    # Create entity if it doesn't exist
    if entity_key not in memory["entities"]:
        memory["entities"][entity_key] = {
            "type": entity_type,
            "observations": [],
            "relations": []
        }
    
    # Check observation limit for this entity
    max_obs_per_entity = settings.get("max_observations_per_entity", 100)
    observations = memory["entities"][entity_key]["observations"]
    
    if len(observations) >= max_obs_per_entity:
        # Remove oldest/least relevant observation
        obs_with_relevance = []
        for obs in observations:
            relevance = calculate_memory_relevance(
                obs["timestamp"],
                obs.get("access_count", 1)
            )
            obs_with_relevance.append((relevance, obs))
        
        obs_with_relevance.sort(key=lambda x: x[0], reverse=True)
        memory["entities"][entity_key]["observations"] = [
            obs for _, obs in obs_with_relevance[:max_obs_per_entity - 1]
        ]
    
    # Add observation
    obs = {
        "content": observation,
        "timestamp": datetime.now().isoformat() + "Z",
        "confidence": confidence,
        "access_count": 1
    }
    if source:
        obs["source"] = source
    if tags:
        obs["tags"] = tags
    
    memory["entities"][entity_key]["observations"].append(obs)
    
    # Update statistics
    memory["statistics"]["total_observations"] += 1
    if len(memory["entities"][entity_key]["observations"]) == 1:
        memory["statistics"]["total_entities"] += 1
    
    # Save updated memory
    save_memory_index(memory)
    
    # Log event
    append_memory_event("observation_added", {
        "entity": entity_key,
        "type": entity_type,
        "observation": observation[:100]  # Only log first 100 chars for privacy
    })
    
    return memory

def add_memory_episode(task_name: str, learnings: list, patterns: list = None, success: bool = True):
    """Add an episode (task completion) to memory."""
    # Privacy check on task name and learnings
    if contains_forbidden_pattern(task_name):
        return None
    
    # Filter learnings for privacy
    safe_learnings = []
    for learning in learnings:
        if not contains_forbidden_pattern(learning):
            safe_learnings.append(learning)
    
    if not safe_learnings:
        return None  # No safe learnings to store
    
    memory = load_memory_index()
    config = get_memory_config()
    settings = config.get("settings", {})
    
    # Check episode limit
    max_episodes = settings.get("max_episodes", 1000)
    if len(memory["episodes"]) >= max_episodes:
        # Prune before adding new episode
        prune_memory_by_relevance()
        memory = load_memory_index()  # Reload after pruning
    
    episode = {
        "id": f"ep_{len(memory['episodes']) + 1:03d}",
        "task": task_name,
        "timestamp": datetime.now().isoformat() + "Z",
        "learnings": safe_learnings,
        "success": success
    }
    if patterns:
        episode["patterns_detected"] = patterns
    
    memory["episodes"].append(episode)
    memory["statistics"]["total_episodes"] += 1
    
    # Save updated memory
    save_memory_index(memory)
    
    # Log event
    append_memory_event("episode_added", {
        "task": task_name,
        "learnings_count": len(safe_learnings)
    })
    
    return memory

def query_memory_semantic(query: str, memory_type: str = None) -> list:
    """Query memory for relevant observations (simple keyword matching for now)."""
    memory = load_memory_index()
    results = []
    query_lower = query.lower()
    
    # Search through entities
    for entity_key, entity_data in memory["entities"].items():
        if memory_type and entity_data["type"] != memory_type:
            continue
            
        for obs in entity_data["observations"]:
            if query_lower in obs["content"].lower() or query_lower in entity_key.lower():
                results.append({
                    "entity": entity_key,
                    "type": entity_data["type"],
                    "observation": obs["content"],
                    "confidence": obs["confidence"],
                    "timestamp": obs["timestamp"]
                })
    
    # Search through episodes
    for episode in memory["episodes"]:
        for learning in episode["learnings"]:
            if query_lower in learning.lower():
                results.append({
                    "type": "episode",
                    "task": episode["task"],
                    "learning": learning,
                    "timestamp": episode["timestamp"]
                })
    
    # Sort by timestamp (most recent first)
    results.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return results

def get_contextual_memory(task_name: str = None, affected_files: list = None) -> dict:
    """Get memory relevant to current context."""
    memory = load_memory_index()
    context = {
        "relevant_entities": {},
        "recent_episodes": [],
        "user_preferences": []
    }
    
    # Get user preferences
    for entity_key, entity_data in memory["entities"].items():
        if entity_data["type"] == "user_preference":
            for obs in entity_data["observations"]:
                context["user_preferences"].append(obs["content"])
    
    # Get recent episodes for similar tasks
    if task_name:
        for episode in memory["episodes"][-10:]:  # Last 10 episodes
            if task_name in episode["task"] or episode["task"] in task_name:
                context["recent_episodes"].append(episode)
    
    # Get entities related to affected files
    if affected_files:
        for file_path in affected_files:
            if file_path in memory["entities"]:
                context["relevant_entities"][file_path] = memory["entities"][file_path]
    
    return context

def calculate_memory_relevance(observation_timestamp: str, access_count: int = 1) -> float:
    """Calculate relevance score with temporal decay."""
    import math
    config = get_memory_config()
    
    if not config["settings"]["decay_enabled"]:
        return 1.0
    
    # Calculate age in days
    obs_time = datetime.fromisoformat(observation_timestamp.replace("Z", "+00:00"))
    age_days = (datetime.now().astimezone() - obs_time).days
    
    # Apply exponential decay with access count boost
    decay_lambda = config["settings"]["decay_lambda"]
    base_score = math.exp(-decay_lambda * age_days)
    
    # Boost score based on access count (logarithmic)
    access_boost = 1 + (0.1 * math.log(access_count + 1))
    
    return min(1.0, base_score * access_boost)