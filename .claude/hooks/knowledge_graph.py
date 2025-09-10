#!/usr/bin/env python3

import json
import os
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from collections import defaultdict
import hashlib

class KnowledgeGraph:
    def __init__(self, base_path: str = ".claude/state/knowledge-graph"):
        self.base_path = base_path
        self.graph_path = os.path.join(base_path, "graph.json")
        self.index_path = os.path.join(base_path, "index.json")
        self.snapshots_path = os.path.join(base_path, "snapshots")
        
        self.nodes = {}  # file_path -> node_data
        self.edges = defaultdict(set)  # file_path -> set of related files
        self.indexes = {
            "components": defaultdict(set),  # component_name -> set of files
            "imports": defaultdict(set),  # module -> set of files importing it
            "exports": defaultdict(set),  # module -> set of files exporting it
            "patterns": defaultdict(set),  # pattern_name -> set of files
            "dependencies": defaultdict(set),  # package -> set of files using it
        }
        self.metadata = {
            "last_updated": None,
            "version": "1.0",
            "stats": {}
        }
        
        self._load()
    
    def _load(self):
        """Load existing graph from disk"""
        if os.path.exists(self.graph_path):
            try:
                with open(self.graph_path, 'r') as f:
                    data = json.load(f)
                    self.nodes = data.get("nodes", {})
                    self.edges = defaultdict(set, {k: set(v) for k, v in data.get("edges", {}).items()})
                    self.metadata = data.get("metadata", self.metadata)
            except Exception:
                pass
        
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, 'r') as f:
                    data = json.load(f)
                    for idx_name, idx_data in data.items():
                        if idx_name in self.indexes:
                            self.indexes[idx_name] = defaultdict(set, {k: set(v) for k, v in idx_data.items()})
            except Exception:
                pass
    
    def save(self):
        """Persist graph to disk"""
        os.makedirs(self.base_path, exist_ok=True)
        
        # Update metadata
        self.metadata["last_updated"] = datetime.now().isoformat()
        self.metadata["stats"] = {
            "total_nodes": len(self.nodes),
            "total_edges": sum(len(edges) for edges in self.edges.values()),
            "indexed_components": len(self.indexes["components"]),
            "indexed_imports": len(self.indexes["imports"]),
        }
        
        # Save main graph
        graph_data = {
            "nodes": self.nodes,
            "edges": {k: list(v) for k, v in self.edges.items()},
            "metadata": self.metadata
        }
        with open(self.graph_path, 'w') as f:
            json.dump(graph_data, f, indent=2)
        
        # Save indexes
        index_data = {name: {k: list(v) for k, v in idx.items()} 
                      for name, idx in self.indexes.items()}
        with open(self.index_path, 'w') as f:
            json.dump(index_data, f, indent=2)
    
    def snapshot(self, reason: str = "manual"):
        """Create a versioned snapshot"""
        os.makedirs(self.snapshots_path, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_file = os.path.join(self.snapshots_path, f"graph_{timestamp}_{reason}.json")
        
        snapshot_data = {
            "nodes": self.nodes,
            "edges": {k: list(v) for k, v in self.edges.items()},
            "indexes": {name: {k: list(v) for k, v in idx.items()} 
                       for name, idx in self.indexes.items()},
            "metadata": self.metadata,
            "snapshot_time": datetime.now().isoformat(),
            "reason": reason
        }
        
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot_data, f, indent=2)
    
    def add_node(self, file_path: str, node_data: Dict[str, Any]):
        """Add or update a node in the graph"""
        # Compute content hash for change detection
        content_hash = None
        if "content" in node_data:
            content_hash = hashlib.md5(node_data["content"].encode()).hexdigest()
            node_data["content_hash"] = content_hash
            del node_data["content"]  # Don't store full content
        
        # Check if node changed
        if file_path in self.nodes:
            old_hash = self.nodes[file_path].get("content_hash")
            if old_hash == content_hash:
                return False  # No change
        
        # Update node
        self.nodes[file_path] = {
            **node_data,
            "last_analyzed": datetime.now().isoformat()
        }
        return True
    
    def add_edge(self, from_file: str, to_file: str, edge_type: str = "imports"):
        """Add an edge between two files"""
        edge_key = f"{from_file}:{edge_type}"
        self.edges[edge_key].add(to_file)
    
    def add_to_index(self, index_name: str, key: str, file_path: str):
        """Add a file to an index"""
        if index_name in self.indexes:
            self.indexes[index_name][key].add(file_path)
    
    def get_related_files(self, file_path: str, depth: int = 1) -> Set[str]:
        """Get all files related to a given file up to specified depth"""
        related = set()
        to_process = {file_path}
        
        for _ in range(depth):
            next_level = set()
            for current in to_process:
                # Direct edges
                for edge_key in self.edges:
                    if edge_key.startswith(f"{current}:"):
                        next_level.update(self.edges[edge_key])
                # Reverse edges
                for edge_key, targets in self.edges.items():
                    if current in targets:
                        source = edge_key.split(":")[0]
                        next_level.add(source)
            
            related.update(next_level)
            to_process = next_level - related
        
        return related - {file_path}
    
    def query_index(self, index_name: str, key: str) -> Set[str]:
        """Query an index for files"""
        if index_name in self.indexes:
            return self.indexes[index_name].get(key, set())
        return set()
    
    def search_patterns(self, pattern: str) -> Dict[str, Set[str]]:
        """Search for files matching a pattern across all indexes"""
        results = {}
        for index_name, index_data in self.indexes.items():
            for key, files in index_data.items():
                if pattern.lower() in key.lower():
                    results[f"{index_name}:{key}"] = files
        return results
    
    def get_context_for_task(self, keywords: List[str]) -> Dict[str, Any]:
        """Get relevant context for a task based on keywords"""
        context = {
            "direct_matches": set(),
            "related_files": set(),
            "components": set(),
            "patterns": set()
        }
        
        for keyword in keywords:
            # Search all indexes
            matches = self.search_patterns(keyword)
            for match_key, files in matches.items():
                context["direct_matches"].update(files)
                
                # Get related files for each match
                for file in files:
                    context["related_files"].update(self.get_related_files(file))
        
        # Get component and pattern info
        for file in context["direct_matches"]:
            if file in self.nodes:
                node = self.nodes[file]
                if "components" in node:
                    context["components"].update(node["components"])
                if "patterns" in node:
                    context["patterns"].update(node["patterns"])
        
        return {k: list(v) if isinstance(v, set) else v for k, v in context.items()}
    
    def cleanup_old_snapshots(self, keep_last: int = 10):
        """Remove old snapshots, keeping only the most recent ones"""
        if not os.path.exists(self.snapshots_path):
            return
        
        snapshots = sorted([f for f in os.listdir(self.snapshots_path) if f.endswith('.json')])
        if len(snapshots) > keep_last:
            for snapshot in snapshots[:-keep_last]:
                os.remove(os.path.join(self.snapshots_path, snapshot))