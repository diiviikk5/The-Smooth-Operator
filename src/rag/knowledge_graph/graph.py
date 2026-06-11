import logging
from typing import Dict, Any, List, Set, Tuple
import json

logger = logging.getLogger(__name__)

class KnowledgeGraph:
    \"\"\"NetworkX-based Knowledge Graph for lead profiling and outreach context augmentation.\"\"\"

    def __init__(self):
        self.nx = None
        self.graph = None
        
        try:
            import networkx as nx
            self.nx = nx
            self.graph = nx.DiGraph()
            logger.info("Initialized NetworkX directed Knowledge Graph")
        except ImportError:
            logger.warning("networkx not installed. KnowledgeGraph running in mock mode.")
            # Basic in-memory representations
            self.mock_nodes = {} # node -> attrs
            self.mock_edges = [] # list of (u, v, attrs)

    def add_entity(self, name: str, entity_type: str, attributes: Dict[str, Any] = None):
        \"\"\"Adds a node/entity to the graph.\"\"\"
        attrs = attributes or {}
        attrs["type"] = entity_type

        if self.graph is not None:
            self.graph.add_node(name, **attrs)
        else:
            self.mock_nodes[name] = attrs

    def add_relationship(self, source: str, target: str, rel_type: str, attributes: Dict[str, Any] = None):
        \"\"\"Adds an edge/relationship between entities.\"\"\"
        attrs = attributes or {}
        attrs["type"] = rel_type

        if self.graph is not None:
            # Ensure nodes exist
            if not self.graph.has_node(source):
                self.graph.add_node(source, type="Unknown")
            if not self.graph.has_node(target):
                self.graph.add_node(target, type="Unknown")
            self.graph.add_edge(source, target, **attrs)
        else:
            self.mock_edges.append((source, target, attrs))

    def get_related_entities(self, name: str, max_depth: int = 1) -> List[Tuple[str, str, Dict[str, Any]]]:
        \"\"\"Finds all entities related to a given entity up to max_depth.\"\"\"
        relations = []

        if self.graph is not None:
            if not self.graph.has_node(name):
                return []
            
            # Simple BFS to find neighbors
            visited = {name}
            queue = [(name, 0)]
            
            while queue:
                current, depth = queue.pop(0)
                if depth >= max_depth:
                    continue
                
                # Neighbors
                for neighbor in self.graph.neighbors(current):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        edge_data = self.graph.get_edge_data(current, neighbor)
                        relations.append((current, neighbor, edge_data))
                        queue.append((neighbor, depth + 1))
        else:
            # Mock BFS
            for u, v, attrs in self.mock_edges:
                if u == name or v == name:
                    relations.append((u, v, attrs))

        return relations

    def expand_context(self, entity_name: str) -> str:
        \"\"\"Generates a natural-language description of an entity's graph neighborhood.\"\"\"
        relations = self.get_related_entities(entity_name, max_depth=1)
        if not relations:
            return ""

        lines = [f"Knowledge Graph relations for {entity_name}:"]
        for u, v, attrs in relations:
            rel_type = attrs.get("type", "connected_to")
            lines.append(f"- {u} is {rel_type} {v}")
            
        return "\\n".join(lines)

    def serialize(self) -> str:
        if self.graph is not None:
            from networkx.readwrite import json_graph
            data = json_graph.node_link_data(self.graph)
            return json.dumps(data)
        else:
            return json.dumps({
                "nodes": self.mock_nodes,
                "edges": self.mock_edges
            })

    def deserialize(self, graph_json: str):
        data = json.loads(graph_json)
        if self.graph is not None:
            from networkx.readwrite import json_graph
            self.graph = json_graph.node_link_graph(data)
        else:
            self.mock_nodes = data.get("nodes", {})
            self.mock_edges = data.get("edges", [])
