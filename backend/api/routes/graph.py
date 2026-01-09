"""Graph operations API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.graph_fallback import GraphFallback

router = APIRouter(prefix="/graph", tags=["graph"])


class NodeCreate(BaseModel):
    """Node creation request."""

    node_id: str
    label: str = ""
    properties: dict = {}


class EdgeCreate(BaseModel):
    """Edge creation request."""

    source: str
    target: str
    relationship: str = ""
    properties: dict = {}


class NodeQuery(BaseModel):
    """Node query request."""

    label: str | None = None
    properties: dict = {}


# Global graph instance
_graph: GraphFallback | None = None


def get_graph() -> GraphFallback:
    """Get or create graph instance."""
    global _graph
    if _graph is None:
        _graph = GraphFallback()
    return _graph


@router.get("/stats")
async def get_graph_stats():
    """Get graph statistics."""
    graph = get_graph()
    return {
        "nodes": graph.node_count,
        "edges": graph.edge_count,
    }


@router.post("/nodes")
async def create_node(node: NodeCreate):
    """Create a new node."""
    graph = get_graph()
    graph.add_node(
        node.node_id, label=node.label, **node.properties
    )
    return {
        "node_id": node.node_id,
        "message": "Node created",
        "node": graph.get_node(node.node_id),
    }


@router.get("/nodes/{node_id}")
async def get_node(node_id: str):
    """Get a node by ID."""
    graph = get_graph()
    node = graph.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return {"node_id": node_id, "data": node}


@router.get("/nodes")
async def list_nodes():
    """List all nodes."""
    graph = get_graph()
    nodes = {}
    for node_id in graph.graph.nodes():
        nodes[node_id] = graph.get_node(node_id)
    return {"nodes": nodes}


@router.post("/nodes/find")
async def find_nodes(query: NodeQuery):
    """Find nodes by label and/or properties."""
    graph = get_graph()
    matches = graph.find_nodes(label=query.label, **query.properties)
    return {
        "matches": matches,
        "count": len(matches),
    }


@router.post("/edges")
async def create_edge(edge: EdgeCreate):
    """Create a new edge."""
    graph = get_graph()
    # Verify nodes exist
    if graph.get_node(edge.source) is None:
        raise HTTPException(
            status_code=404, detail=f"Source node '{edge.source}' not found"
        )
    if graph.get_node(edge.target) is None:
        raise HTTPException(
            status_code=404, detail=f"Target node '{edge.target}' not found"
        )

    graph.add_edge(
        edge.source, edge.target, relationship=edge.relationship, **edge.properties
    )
    return {
        "source": edge.source,
        "target": edge.target,
        "message": "Edge created",
    }


@router.get("/nodes/{node_id}/neighbors")
async def get_neighbors(node_id: str):
    """Get neighbors of a node."""
    graph = get_graph()
    if graph.get_node(node_id) is None:
        raise HTTPException(status_code=404, detail="Node not found")
    neighbors = graph.get_neighbors(node_id)
    return {
        "node_id": node_id,
        "neighbors": neighbors,
        "count": len(neighbors),
    }


@router.delete("/nodes/{node_id}")
async def delete_node(node_id: str):
    """Delete a node (and its edges)."""
    graph = get_graph()
    if node_id not in graph.graph:
        raise HTTPException(status_code=404, detail="Node not found")
    graph.graph.remove_node(node_id)
    graph.save()
    return {"node_id": node_id, "message": "Node deleted"}


@router.delete("/graph")
async def clear_graph():
    """Clear the entire graph."""
    graph = get_graph()
    graph.clear()
    return {"message": "Graph cleared"}


