"""NetworkX-based graph fallback for offline operation when Neo4j is unavailable."""

import logging
import sqlite3
from pathlib import Path
from typing import Any, Optional

import networkx as nx

logger = logging.getLogger(__name__)


class GraphFallback:
    """
    NetworkX in-memory graph with SQLite persistence.

    Provides local graph storage when Neo4j connection fails or for offline operation.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize graph fallback.

        Args:
            db_path: Path to SQLite database file (default: ./data/henry_graph.db)
        """
        if db_path is None:
            db_path = Path("./data/henry_graph.db")
        else:
            db_path = Path(db_path)

        # Create data directory if it doesn't exist
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self.graph = nx.DiGraph()  # Directed graph
        self._load_from_db()

    def _load_from_db(self) -> None:
        """Load graph from SQLite database."""
        try:
            if not self.db_path.exists():
                logger.info(f"Graph database not found at {self.db_path}, starting fresh")
                return

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create tables if they don't exist
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    label TEXT,
                    properties TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT,
                    target TEXT,
                    relationship TEXT,
                    properties TEXT,
                    FOREIGN KEY (source) REFERENCES nodes(id),
                    FOREIGN KEY (target) REFERENCES nodes(id)
                )
                """
            )

            # Load nodes
            cursor.execute("SELECT id, label, properties FROM nodes")
            for row in cursor.fetchall():
                node_id, label, properties = row
                props = eval(properties) if properties else {}
                self.graph.add_node(node_id, label=label, **props)

            # Load edges
            cursor.execute("SELECT source, target, relationship, properties FROM edges")
            for row in cursor.fetchall():
                source, target, relationship, properties = row
                props = eval(properties) if properties else {}
                self.graph.add_edge(source, target, relationship=relationship, **props)

            conn.close()
            logger.info(f"Loaded graph from {self.db_path}: {len(self.graph.nodes)} nodes, "
                       f"{len(self.graph.edges)} edges")
        except Exception as e:
            logger.error(f"Failed to load graph from database: {e}")
            self.graph = nx.DiGraph()

    def _save_to_db(self) -> None:
        """Save graph to SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create tables if they don't exist
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    label TEXT,
                    properties TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT,
                    target TEXT,
                    relationship TEXT,
                    properties TEXT,
                    FOREIGN KEY (source) REFERENCES nodes(id),
                    FOREIGN KEY (target) REFERENCES nodes(id)
                )
                """
            )

            # Clear existing data
            cursor.execute("DELETE FROM edges")
            cursor.execute("DELETE FROM nodes")

            # Save nodes
            for node_id, data in self.graph.nodes(data=True):
                label = data.get("label", "")
                properties = {k: v for k, v in data.items() if k != "label"}
                cursor.execute(
                    "INSERT INTO nodes (id, label, properties) VALUES (?, ?, ?)",
                    (node_id, label, str(properties)),
                )

            # Save edges
            for source, target, data in self.graph.edges(data=True):
                relationship = data.get("relationship", "")
                properties = {k: v for k, v in data.items() if k != "relationship"}
                cursor.execute(
                    "INSERT INTO edges (source, target, relationship, properties) VALUES (?, ?, ?, ?)",
                    (source, target, relationship, str(properties)),
                )

            conn.commit()
            conn.close()
            logger.debug(f"Saved graph to {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to save graph to database: {e}")

    def add_node(self, node_id: str, label: str = "", **properties) -> None:
        """
        Add a node to the graph.

        Args:
            node_id: Unique node identifier
            label: Node label/type
            **properties: Additional node properties
        """
        self.graph.add_node(node_id, label=label, **properties)
        self._save_to_db()

    def add_edge(
        self, source: str, target: str, relationship: str = "", **properties
    ) -> None:
        """
        Add an edge to the graph.

        Args:
            source: Source node ID
            target: Target node ID
            relationship: Relationship type
            **properties: Additional edge properties
        """
        self.graph.add_edge(source, target, relationship=relationship, **properties)
        self._save_to_db()

    def get_node(self, node_id: str) -> Optional[dict[str, Any]]:
        """
        Get node data.

        Args:
            node_id: Node identifier

        Returns:
            dict: Node data or None if not found
        """
        if node_id in self.graph:
            return dict(self.graph.nodes[node_id])
        return None

    def get_neighbors(self, node_id: str) -> list[str]:
        """
        Get neighbor nodes.

        Args:
            node_id: Node identifier

        Returns:
            list: List of neighbor node IDs
        """
        if node_id not in self.graph:
            return []
        return list(self.graph.neighbors(node_id))

    def find_nodes(self, label: Optional[str] = None, **properties) -> list[str]:
        """
        Find nodes by label and/or properties.

        Args:
            label: Node label to filter by
            **properties: Property filters

        Returns:
            list: List of matching node IDs
        """
        matches = []
        for node_id, data in self.graph.nodes(data=True):
            if label and data.get("label") != label:
                continue
            if all(data.get(k) == v for k, v in properties.items()):
                matches.append(node_id)
        return matches

    def save(self) -> None:
        """Explicitly save graph to database."""
        self._save_to_db()

    def clear(self) -> None:
        """Clear the graph."""
        self.graph.clear()
        self._save_to_db()

    @property
    def node_count(self) -> int:
        """Get number of nodes."""
        return len(self.graph.nodes)

    @property
    def edge_count(self) -> int:
        """Get number of edges."""
        return len(self.graph.edges)


