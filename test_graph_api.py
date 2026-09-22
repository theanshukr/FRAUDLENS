import urllib.request
import json
import time

cases = ["HHG-001", "HHG-002", "HHG-004", "HHG-005", "HHG-017"]

for case_id in cases:
    try:
        url = f"http://localhost:8000/api/investigations/{case_id}/graph"
        req = urllib.request.urlopen(url)
        data = json.loads(req.read())
        
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        
        node_types = set([n.get("type") for n in nodes])
        edge_types = set([e.get("type") for e in edges])
        
        print(f"[{case_id}]")
        print(f"  Nodes: {len(nodes)}")
        print(f"  Edges: {len(edges)}")
        print(f"  Node Types: {', '.join(node_types)}")
        print(f"  Edge Types: {', '.join(edge_types)}")
        print()
    except Exception as e:
        print(f"[{case_id}] Error: {e}")
