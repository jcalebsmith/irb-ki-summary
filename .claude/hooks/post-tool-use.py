#!/usr/bin/env python3
"""Post-tool-use hook to remind about DAIC command in implementation mode."""
import json
import sys
from pathlib import Path
from shared_state import check_daic_mode_bool, get_project_root

# Import memory capture functions
sys.path.insert(0, str(Path(__file__).parent))
try:
    from memory_capture import process_tool_use
    MEMORY_ENABLED = True
except ImportError:
    MEMORY_ENABLED = False

# Load input
input_data = json.load(sys.stdin)
tool_name = input_data.get("tool_name", "")
tool_input = input_data.get("tool_input", {})
cwd = input_data.get("cwd", "")
mod = False

# Check if we're in a subagent context
project_root = get_project_root()
subagent_flag = project_root / '.claude' / 'state' / 'in_subagent_context.flag'
in_subagent = subagent_flag.exists()

# If this is the Task tool completing, clear the subagent flag
if tool_name == "Task" and in_subagent:
    subagent_flag.unlink()
    # Don't show DAIC reminder for Task completion
    in_subagent = True

# Capture tool use in memory if enabled
if MEMORY_ENABLED and not in_subagent:
    try:
        tool_data = {
            "tool_name": tool_name,
            "parameters": tool_input,
            "cwd": cwd
        }
        process_tool_use(tool_data)
    except Exception:
        # Silently fail to not disrupt workflow
        pass

# Check current mode
discussion_mode = check_daic_mode_bool()

# Only remind if in implementation mode AND not in a subagent
implementation_tools = ["Edit", "Write", "MultiEdit", "NotebookEdit"]
if not discussion_mode and tool_name in implementation_tools and not in_subagent:
    # Output reminder
    print("[DAIC Reminder] When you're done implementing, run: daic", file=sys.stderr)
    mod = True

# Check for cd command in Bash operations
if tool_name == "Bash":
    command = tool_input.get("command", "")
    if "cd " in command:
        print(f"[CWD: {cwd}]", file=sys.stderr)
        mod = True

if mod:
    sys.exit(2)  # Exit code 2 feeds stderr back to Claude
else:
    sys.exit(0)