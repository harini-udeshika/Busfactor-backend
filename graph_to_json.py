import json

def graph_to_json(graph, centrality):
    nodes = [
        {"id": node, "size": centrality[node],"class": graph.nodes[node].get('class', None)} for node in graph.nodes()
    ]
    edges = [
        {"source": u, "target": v, "weight": d.get("weight", 1)}
        for u, v, d in graph.edges(data=True)
    ]
    return {"nodes": nodes, "edges": edges}
