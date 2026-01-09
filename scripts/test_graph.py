#!/usr/bin/env python3
"""Interactive script to test graph generation and operations."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.graph_fallback import GraphFallback


def main():
    """Test graph operations interactively."""
    print("=" * 60)
    print("H.E.N.R.Y. Graph Fallback Testing")
    print("=" * 60)
    print()

    # Create a test graph
    db_path = project_root / "data" / "test_graph.db"
    print(f"Creating graph at: {db_path}")
    graph = GraphFallback(str(db_path))

    print(f"\nInitial state: {graph.node_count} nodes, {graph.edge_count} edges")
    print()

    # Add some nodes
    print("Adding nodes...")
    graph.add_node("user", label="Person", name="You", role="user")
    graph.add_node("henry", label="Assistant", name="HENRY", role="assistant")
    graph.add_node("idea1", label="Idea", title="Test Idea", content="This is a test idea")
    graph.add_node("concept1", label="Concept", name="Productivity", category="work")

    print(f"  ✓ Added 4 nodes")
    print(f"  Current: {graph.node_count} nodes, {graph.edge_count} edges")
    print()

    # Add relationships
    print("Adding relationships...")
    graph.add_edge("user", "henry", relationship="USES", since="2024")
    graph.add_edge("user", "idea1", relationship="CREATED", timestamp="2024-01-01")
    graph.add_edge("idea1", "concept1", relationship="RELATED_TO", strength=0.8)
    graph.add_edge("henry", "idea1", relationship="KNOWS_ABOUT")

    print(f"  ✓ Added 4 relationships")
    print(f"  Current: {graph.node_count} nodes, {graph.edge_count} edges")
    print()

    # Query nodes
    print("Querying nodes...")
    print(f"  All nodes: {list(graph.graph.nodes())}")
    print()

    # Get specific node
    print("Getting node details...")
    user_node = graph.get_node("user")
    print(f"  User node: {user_node}")
    print()

    # Find nodes by label
    print("Finding nodes by label...")
    persons = graph.find_nodes(label="Person")
    ideas = graph.find_nodes(label="Idea")
    print(f"  Persons: {persons}")
    print(f"  Ideas: {ideas}")
    print()

    # Find nodes by properties
    print("Finding nodes by properties...")
    user_nodes = graph.find_nodes(name="You")
    print(f"  Nodes with name='You': {user_nodes}")
    print()

    # Get neighbors
    print("Getting neighbors...")
    user_neighbors = graph.get_neighbors("user")
    print(f"  User's neighbors: {user_neighbors}")
    print()

    # Show graph structure
    print("Graph structure:")
    print("  Nodes:")
    for node_id in graph.graph.nodes():
        data = graph.get_node(node_id)
        print(f"    - {node_id}: {data}")
    print()
    print("  Edges:")
    for source, target, data in graph.graph.edges(data=True):
        rel = data.get("relationship", "UNKNOWN")
        print(f"    - {source} --[{rel}]--> {target}")

    print()
    print("=" * 60)
    print("Graph saved to database!")
    print(f"Database location: {db_path}")
    print()
    print("To test persistence, run this script again -")
    print("the graph will load from the database.")
    print("=" * 60)


if __name__ == "__main__":
    main()


