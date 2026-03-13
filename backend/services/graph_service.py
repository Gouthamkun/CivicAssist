
import json
import os
from typing import List, Dict, Optional

class GraphService:
    def __init__(self):
        self.graph_data = self.load_graph()

    def load_graph(self) -> Dict:
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "process_graph.json")
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading graph: {e}")
            return {"domains": {}}

    def get_domain_graph(self, domain_name: str) -> Dict:
        return self.graph_data.get("domains", {}).get(domain_name, {"nodes": [], "edges": []})

    def get_neighbors(self, domain_name: str, node_id: str) -> List[Dict]:
        domain = self.get_domain_graph(domain_name)
        neighbors = []
        for edge in domain.get("edges", []):
            if edge["source"] == node_id:
                target_node = next((n for n in domain["nodes"] if n["id"] == edge["target"]), None)
                if target_node:
                    neighbors.append({
                        "node": target_node,
                        "relation": edge["relation"],
                        "direction": "outgoing"
                    })
            elif edge["target"] == node_id:
                source_node = next((n for n in domain["nodes"] if n["id"] == edge["source"]), None)
                if source_node:
                    neighbors.append({
                        "node": source_node,
                        "relation": edge["relation"],
                        "direction": "incoming"
                    })
        return neighbors

    def find_process_path(self, domain_name: str, start_node_id: str, end_node_id: str) -> List[str]:
        # Simple BFS for pathfinding in the specific domain
        domain = self.get_domain_graph(domain_name)
        edges = domain.get("edges", [])
        
        queue = [[start_node_id]]
        visited = set()
        
        while queue:
            path = queue.pop(0)
            node = path[-1]
            if node == end_node_id:
                return path
            
            if node not in visited:
                visited.add(node)
                for edge in edges:
                    if edge["source"] == node:
                        new_path = list(path)
                        new_path.append(edge["target"])
                        queue.append(new_path)
        return []

    def get_reasoning_chain(self, domain_name: str, node_id: str) -> List[str]:
        # Backwards traversal to find the 'root' reason/status
        domain = self.get_domain_graph(domain_name)
        edges = domain.get("edges", [])
        
        chain = [node_id]
        current = node_id
        
        # Max 5 levels to avoid infinite loops if graph has cycles
        for _ in range(5):
            found_parent = False
            for edge in edges:
                if edge["target"] == current:
                    current = edge["source"]
                    chain.insert(0, current)
                    found_parent = True
                    break
            if not found_parent:
                break
        return chain

graph_service = GraphService()
