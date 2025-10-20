#!/usr/bin/env python3

import sys
import json
import os
import re
from pathlib import Path

# Add parent directory to path for importing knowledge_graph
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from knowledge_graph import KnowledgeGraph
from shared_state import SharedState

def extract_file_metadata(file_path: str, content: str = None) -> dict:
    """Extract metadata from file content"""
    metadata = {
        "file_type": Path(file_path).suffix,
        "components": set(),
        "imports": set(),
        "exports": set(),
        "patterns": set(),
        "functions": set(),
        "classes": set()
    }
    
    if not content:
        return {k: list(v) if isinstance(v, set) else v for k, v in metadata.items()}
    
    # Language-specific parsing
    ext = Path(file_path).suffix
    
    if ext in ['.js', '.jsx', '.ts', '.tsx']:
        # JavaScript/TypeScript imports
        import_patterns = [
            r"import\s+(?:[\w{},\s*]+\s+from\s+)?['\"]([^'\"]+)['\"]",
            r"require\s*\(['\"]([^'\"]+)['\"]\)",
            r"from\s+['\"]([^'\"]+)['\"]"
        ]
        for pattern in import_patterns:
            for match in re.finditer(pattern, content):
                metadata["imports"].add(match.group(1))
        
        # Exports
        export_patterns = [
            r"export\s+(?:default\s+)?(?:class|function|const|let|var)\s+(\w+)",
            r"export\s*{\s*([^}]+)\s*}",
            r"module\.exports\s*=\s*(\w+)"
        ]
        for pattern in export_patterns:
            for match in re.finditer(pattern, content):
                if pattern == export_patterns[1]:  # Handle multiple exports
                    exports = match.group(1).split(',')
                    for exp in exports:
                        metadata["exports"].add(exp.strip().split(' as ')[0])
                else:
                    metadata["exports"].add(match.group(1))
        
        # React components
        component_patterns = [
            r"(?:export\s+)?(?:const|function)\s+(\w+)\s*[=:]\s*(?:\([^)]*\)\s*=>|\([^)]*\):\s*JSX\.Element)",
            r"(?:export\s+)?class\s+(\w+)\s+extends\s+(?:React\.)?Component"
        ]
        for pattern in component_patterns:
            for match in re.finditer(pattern, content):
                metadata["components"].add(match.group(1))
        
        # Functions and classes
        for match in re.finditer(r"(?:async\s+)?function\s+(\w+)", content):
            metadata["functions"].add(match.group(1))
        for match in re.finditer(r"class\s+(\w+)", content):
            metadata["classes"].add(match.group(1))
    
    elif ext in ['.py']:
        # Python imports
        for match in re.finditer(r"(?:from\s+([^\s]+)\s+)?import\s+([^\n]+)", content):
            module = match.group(1) or match.group(2).split(',')[0].strip()
            metadata["imports"].add(module)
        
        # Functions and classes
        for match in re.finditer(r"def\s+(\w+)\s*\(", content):
            metadata["functions"].add(match.group(1))
        for match in re.finditer(r"class\s+(\w+)", content):
            metadata["classes"].add(match.group(1))
    
    elif ext in ['.go']:
        # Go imports
        for match in re.finditer(r'import\s+(?:\([^)]+\)|"[^"]+")', content):
            import_block = match.group(0)
            for imp in re.finditer(r'"([^"]+)"', import_block):
                metadata["imports"].add(imp.group(1))
        
        # Functions and types
        for match in re.finditer(r"func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(", content):
            metadata["functions"].add(match.group(1))
        for match in re.finditer(r"type\s+(\w+)\s+(?:struct|interface)", content):
            metadata["classes"].add(match.group(1))
    
    # Detect common patterns
    patterns_to_check = {
        "singleton": r"(?:getInstance|singleton|INSTANCE)",
        "factory": r"(?:create\w+|factory|Factory)",
        "observer": r"(?:subscribe|unsubscribe|notify|observer)",
        "async": r"(?:async|await|Promise|then)",
        "hooks": r"(?:use[A-Z]\w+|hook)",
        "api": r"(?:fetch|axios|request|endpoint)",
        "state": r"(?:setState|useState|state|State)",
        "context": r"(?:Context|Provider|Consumer|useContext)"
    }
    
    for pattern_name, pattern_regex in patterns_to_check.items():
        if re.search(pattern_regex, content, re.IGNORECASE):
            metadata["patterns"].add(pattern_name)
    
    # Convert sets to lists for JSON serialization
    return {k: list(v) if isinstance(v, set) else v for k, v in metadata.items()}

def find_relationships(file_path: str, metadata: dict, kg: KnowledgeGraph):
    """Find and add relationships between files"""
    # Add import relationships
    for imp in metadata.get("imports", []):
        # Try to resolve the import to a file
        possible_paths = []
        
        if imp.startswith('.'):
            # Relative import
            base_dir = os.path.dirname(file_path)
            import_path = os.path.normpath(os.path.join(base_dir, imp))
            possible_paths = [
                import_path,
                f"{import_path}.js",
                f"{import_path}.ts",
                f"{import_path}.jsx",
                f"{import_path}.tsx",
                f"{import_path}/index.js",
                f"{import_path}/index.ts"
            ]
        else:
            # Package import - check node_modules or src
            possible_paths = [
                f"node_modules/{imp}",
                f"src/{imp}",
                f"src/{imp}.js",
                f"src/{imp}.ts"
            ]
        
        for path in possible_paths:
            if os.path.exists(path):
                kg.add_edge(file_path, path, "imports")
                break
    
    # Add component relationships
    for component in metadata.get("components", []):
        kg.add_to_index("components", component, file_path)
    
    # Add pattern relationships
    for pattern in metadata.get("patterns", []):
        kg.add_to_index("patterns", pattern, file_path)
    
    # Add function/class index entries
    for func in metadata.get("functions", []):
        kg.add_to_index("exports", func, file_path)
    for cls in metadata.get("classes", []):
        kg.add_to_index("exports", cls, file_path)

def main():
    # Get tool input from stdin
    try:
        tool_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError) as e:
        # Silently exit if no valid JSON input
        sys.exit(0)
    
    tool_name = tool_input.get("tool", "")
    params = tool_input.get("params", {})
    
    # Only process Read and Edit tools
    if tool_name not in ["Read", "Edit", "MultiEdit"]:
        sys.exit(0)
    
    # Get file path
    file_path = params.get("file_path", "")
    if not file_path or not os.path.exists(file_path):
        sys.exit(0)
    
    # Skip non-code files
    ext = Path(file_path).suffix
    if ext not in ['.js', '.jsx', '.ts', '.tsx', '.py', '.go', '.java', '.rs', '.cpp', '.c', '.h']:
        sys.exit(0)
    
    # Initialize or get knowledge graph from shared state
    state = SharedState()
    kg = state.get("knowledge_graph")
    if kg is None:
        kg = KnowledgeGraph()
        state.set("knowledge_graph", kg)
    
    # For Read operations, analyze the file
    if tool_name == "Read":
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Extract metadata
            metadata = extract_file_metadata(file_path, content)
            metadata["content"] = content  # Include for hash computation
            
            # Add/update node
            if kg.add_node(file_path, metadata):
                # Node changed, update relationships
                find_relationships(file_path, metadata, kg)
                
                # Save periodically (every 10 changes)
                changes = state.get("kg_changes", 0) + 1
                state.set("kg_changes", changes)
                if changes % 10 == 0:
                    kg.save()
        except Exception:
            pass  # Silently handle errors
    
    # For Edit operations, mark file as modified
    elif tool_name in ["Edit", "MultiEdit"]:
        if file_path in kg.nodes:
            kg.nodes[file_path]["needs_reanalysis"] = True
            state.set("kg_modified", True)

if __name__ == "__main__":
    main()