"""Tests for graph fallback."""

import tempfile
from pathlib import Path

import pytest

from backend.services.graph_fallback import GraphFallback


def test_graph_fallback_initialization():
    """Test graph fallback initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        graph = GraphFallback(str(db_path))

        assert graph.node_count == 0
        assert graph.edge_count == 0


def test_add_node():
    """Test adding a node."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        graph = GraphFallback(str(db_path))

        graph.add_node("node1", label="TestNode", prop1="value1")
        assert graph.node_count == 1

        node = graph.get_node("node1")
        assert node is not None
        assert node["label"] == "TestNode"
        assert node["prop1"] == "value1"


def test_add_edge():
    """Test adding an edge."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        graph = GraphFallback(str(db_path))

        graph.add_node("node1", label="Node1")
        graph.add_node("node2", label="Node2")
        graph.add_edge("node1", "node2", relationship="RELATED_TO", weight=1.0)

        assert graph.edge_count == 1
        neighbors = graph.get_neighbors("node1")
        assert "node2" in neighbors


def test_find_nodes():
    """Test finding nodes by label and properties."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        graph = GraphFallback(str(db_path))

        graph.add_node("node1", label="Person", name="Alice", age=30)
        graph.add_node("node2", label="Person", name="Bob", age=25)
        graph.add_node("node3", label="Place", name="Paris")

        # Find by label
        persons = graph.find_nodes(label="Person")
        assert len(persons) == 2
        assert "node1" in persons
        assert "node2" in persons

        # Find by properties
        alice = graph.find_nodes(name="Alice")
        assert len(alice) == 1
        assert "node1" in alice


def test_persistence():
    """Test that graph persists to database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Create graph and add data
        graph1 = GraphFallback(str(db_path))
        graph1.add_node("node1", label="Test")
        graph1.add_node("node2", label="Test")  # Add node2 explicitly before edge
        graph1.add_edge("node1", "node2", relationship="RELATED_TO")

        # Create new graph instance and load
        graph2 = GraphFallback(str(db_path))
        assert graph2.node_count == 2  # Both nodes should be present
        assert graph2.edge_count == 1


