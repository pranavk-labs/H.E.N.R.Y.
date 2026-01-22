"""Knowledge service using Neo4jClient directly with optional local fallback.

This provides a higher-level API for working with user preferences,
ideas, and concepts. Uses Neo4jClient directly (no adapter layer),
with optional fallback to local GraphFallback for offline operation (requires networkx).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from backend.services.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

# Optional import - GraphFallback only available if networkx is installed
try:
    from backend.services.graph_fallback import GraphFallback
    GRAPH_FALLBACK_AVAILABLE = True
except ImportError:
    if TYPE_CHECKING:
        from backend.services.graph_fallback import GraphFallback
    GraphFallback = None  # type: ignore
    GRAPH_FALLBACK_AVAILABLE = False
    logger.warning(
        "NetworkX not available - graph fallback disabled. "
        "Neo4j is required. Install networkx for offline support: pip install networkx"
    )


def _utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Idea:
    """Simple representation of an idea node."""

    id: str
    text: str
    tags: List[str]
    created_at: str
    updated_at: Optional[str] = None


@dataclass
class Preference:
    """Simple representation of a user preference."""

    id: str
    user_id: str
    key: str
    value: Any
    strength: float
    created_at: str
    updated_at: Optional[str] = None


@dataclass
class Category:
    """Simple representation of a todo category."""

    id: str
    name: str
    color: str
    icon: str
    created_at: str
    updated_at: Optional[str] = None


@dataclass
class Todo:
    """Simple representation of a todo/task node."""

    id: str
    title: str
    description: str
    status: str  # todo, in_progress, completed, cancelled
    priority: str  # low, medium, high, critical
    difficulty: int  # 1-5 scale
    category_id: Optional[str]
    due_date: Optional[str]
    estimated_minutes: Optional[int]
    recurrence_pattern: str  # none, daily, weekly, monthly
    parent_todo_id: Optional[str]
    created_at: str
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None


class KnowledgeService:
    """High-level knowledge service using Neo4jClient directly with optional local fallback."""

    _instance: Optional["KnowledgeService"] = None

    def __init__(self, graph: Optional["GraphFallback"] = None) -> None:
        # Only use GraphFallback if networkx is available
        if graph is not None:
            self._graph = graph
        elif GRAPH_FALLBACK_AVAILABLE and GraphFallback is not None:
            self._graph = GraphFallback()
        else:
            self._graph = None
            logger.info("KnowledgeService initialized without fallback - Neo4j required")

        self._neo4j_client = Neo4jClient.get_instance()
        self._use_neo4j = True  # Try Neo4j first
        self._preferences_cache: Dict[str, List[Preference]] = {}  # Cache preferences by user_id

    @classmethod
    def get_instance(cls) -> "KnowledgeService":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create event loop for async operations."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Event loop is closed")
            return loop
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def _run_async(self, coro):
        """Run async coroutine, handling already-running event loop gracefully.

        Args:
            coro: Coroutine to run

        Returns:
            Result of the coroutine, or None if event loop is already running

        Raises:
            Exception: If an error occurs other than event loop already running
        """
        try:
            loop = self._get_loop()
            return loop.run_until_complete(coro)
        except RuntimeError as e:
            # If event loop is already running, we're being called from async context
            # This is fine - we'll just use the fallback
            if "already running" in str(e):
                return None
            raise

    def _ensure_neo4j_connected(self) -> bool:
        """Ensure Neo4j is connected, return True if successful."""
        if not self._neo4j_client.is_connected:
            try:
                result = self._run_async(self._neo4j_client.connect())
                # If result is None, event loop was already running - fall back
                return result is not None
            except Exception as e:
                logger.debug(f"Neo4j not available: {e}")
                return False
        return True

    def _write_node(self, node_id: str, label: str, **properties: Any) -> None:
        """Write node to Neo4j if available, otherwise to fallback."""
        if self._use_neo4j and self._ensure_neo4j_connected():
            try:
                async def _create():
                    async with self._neo4j_client.driver.session() as session:
                        props_str = ", ".join(f"{k}: ${k}" for k in properties.keys())
                        query = f"CREATE (n:{label} {{id: $id, {props_str}}}) RETURN n"
                        params = {"id": node_id, **properties}
                        result = await session.run(query, params)
                        await result.consume()

                self._run_async(_create())
                logger.debug(f"Wrote node {node_id} to Neo4j")
                # Also write to fallback for redundancy
                self._graph.add_node(node_id, label=label, **properties)
                return
            except RuntimeError as e:
                # Silently fall back if event loop is already running
                if "already running" not in str(e):
                    logger.info(f"Neo4j write failed: {e}, falling back to local graph")
                    self._use_neo4j = False
            except Exception as e:
                logger.info(f"Neo4j write failed: {e}, falling back to local graph")
                self._use_neo4j = False

        # Fallback to local graph
        self._graph.add_node(node_id, label=label, **properties)

    def _read_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Read node from Neo4j if available, otherwise from fallback."""
        if self._use_neo4j and self._ensure_neo4j_connected():
            try:
                async def _get():
                    async with self._neo4j_client.driver.session() as session:
                        # Use IS NOT NULL to check property existence and avoid schema warnings
                        result = await session.run(
                            "MATCH (n) WHERE n.id IS NOT NULL AND n.id = $id RETURN n",
                            {"id": node_id}
                        )
                        record = await result.single()
                        if record:
                            return dict(record["n"])
                        return None

                node = self._run_async(_get())
                if node is not None:
                    return node
            except RuntimeError as e:
                # Silently fall back if event loop is already running (called from async context)
                if "already running" in str(e):
                    pass  # Fall through to local graph fallback
                else:
                    logger.debug(f"Neo4j read failed: {e}, trying fallback")
            except Exception as e:
                logger.debug(f"Neo4j read failed: {e}, trying fallback")

        return self._graph.get_node(node_id)

    def _update_node(self, node_id: str, **properties: Any) -> bool:
        """Update node in Neo4j if available, otherwise in fallback."""
        logger.debug(f"_update_node called for {node_id[:8]} with properties: {list(properties.keys())}")
        
        if self._use_neo4j and self._ensure_neo4j_connected():
            try:
                async def _update():
                    async with self._neo4j_client.driver.session() as session:
                        set_clauses = ", ".join(f"n.{k} = ${k}" for k in properties.keys())
                        query = f"MATCH (n) WHERE n.id IS NOT NULL AND n.id = $id SET {set_clauses} RETURN n"
                        params = {"id": node_id, **properties}
                        result = await session.run(query, params)
                        await result.consume()

                self._run_async(_update())  # FIXED: Unindented to actually call the update
                
                # Also update fallback
                data = self._graph.get_node(node_id) or {}
                data.update(properties)
                self._graph.graph.nodes[node_id].update(data)
                self._graph.save()
                logger.info(f"Updated node {node_id[:8]} in Neo4j and fallback")
                return True
            except RuntimeError as e:
                # If event loop is already running, fall back to local graph only
                if "already running" in str(e):
                    logger.debug(f"Event loop already running, using fallback for update")
                    self._use_neo4j = False
                else:
                    logger.debug(f"Neo4j update failed: {e}")
                    self._use_neo4j = False
            except Exception as e:
                logger.debug(f"Neo4j update failed: {e}")
                self._use_neo4j = False

        # Fallback to local graph
        data = self._graph.get_node(node_id)
        if not data:
            logger.warning(f"Node {node_id[:8]} not found in fallback graph")
            return False
        data.update(properties)
        self._graph.graph.nodes[node_id].update(data)
        self._graph.save()
        logger.info(f"Updated node {node_id[:8]} in fallback graph only")
        return True

    def _delete_node(self, node_id: str) -> bool:
        """Delete node from Neo4j if available, otherwise from fallback."""
        if self._use_neo4j and self._ensure_neo4j_connected():
            try:
                async def _delete():
                    async with self._neo4j_client.driver.session() as session:
                        result = await session.run(
                            "MATCH (n) WHERE n.id IS NOT NULL AND n.id = $id DETACH DELETE n", {"id": node_id}
                        )
                        await result.consume()

                        self._run_async(_delete())
                # Also delete from fallback
                if node_id in self._graph.graph:
                    self._graph.graph.remove_node(node_id)
                    self._graph.save()
                return True
            except Exception as e:
                logger.debug(f"Neo4j delete failed: {e}")
                self._use_neo4j = False

        # Fallback to local graph
        if node_id not in self._graph.graph:
            return False
        self._graph.graph.remove_node(node_id)
        self._graph.save()
        return True

    def _find_nodes(
        self, label: Optional[str] = None, **properties: Any
    ) -> List[str]:
        """Find nodes in Neo4j if available, otherwise in fallback."""
        if self._use_neo4j and self._ensure_neo4j_connected():
            try:
                async def _find():
                    async with self._neo4j_client.driver.session() as session:
                        where_clauses = []
                        params: Dict[str, Any] = {}

                        if label:
                            where_clauses.append(f"n:{label}")

                        for key, value in properties.items():
                            where_clauses.append(f"n.{key} = ${key}")
                            params[key] = value

                        where_str = " AND ".join(where_clauses) if where_clauses else "1=1"
                        # Add IS NOT NULL check to avoid schema warnings
                        if where_clauses:
                            query = f"MATCH (n) WHERE n.id IS NOT NULL AND {where_str} RETURN n.id as id"
                        else:
                            query = f"MATCH (n) WHERE n.id IS NOT NULL RETURN n.id as id"
                        result = await session.run(query, params)
                        return [record["id"] async for record in result]

                node_ids = self._run_async(_find())
                if node_ids:
                    return node_ids
            except Exception as e:
                logger.debug(f"Neo4j find failed: {e}")
                self._use_neo4j = False

        return self._graph.find_nodes(label=label, **properties)

    def _list_nodes_by_label(self, label: str) -> List[Dict[str, Any]]:
        """List nodes by label from Neo4j if available, otherwise from fallback."""
        if self._use_neo4j and self._ensure_neo4j_connected():
            try:
                async def _list():
                    async with self._neo4j_client.driver.session() as session:
                        query = f"MATCH (n:{label}) RETURN n"
                        result = await session.run(query)
                        nodes = []
                        async for record in result:
                            node = dict(record["n"])
                            nodes.append(node)
                        return nodes

                nodes = self._run_async(_list())
                if nodes:
                    return nodes
            except Exception as e:
                logger.debug(f"Neo4j list failed: {e}")
                self._use_neo4j = False

        # Fallback: convert from graph format
        nodes = []
        for node_id, data in self._graph.graph.nodes(data=True):
            if data.get("label") == label:
                node_data = dict(data)
                node_data["id"] = node_id
                nodes.append(node_data)
        return nodes

    def _create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        **properties: Any,
    ) -> None:
        """Create relationship in Neo4j if available, otherwise in fallback."""
        if self._use_neo4j and self._ensure_neo4j_connected():
            try:
                async def _create_rel():
                    async with self._neo4j_client.driver.session() as session:
                        props_str = ""
                        if properties:
                            props_str = " {" + ", ".join(f"{k}: ${k}" for k in properties.keys()) + "}"
                        query = (
                            f"MATCH (a), (b) WHERE a.id IS NOT NULL AND b.id IS NOT NULL "
                            f"AND a.id = $source_id AND b.id = $target_id "
                            f"CREATE (a)-[r:{relationship_type}{props_str}]->(b) RETURN r"
                        )
                        params = {"source_id": source_id, "target_id": target_id, **properties}
                        result = await session.run(query, params)
                        await result.consume()

                self._run_async(_create_rel())
                # Also create in fallback
                self._graph.add_edge(
                    source_id, target_id, relationship=relationship_type, **properties
                )
                return
            except Exception as e:
                logger.debug(f"Neo4j relationship creation failed: {e}")
                self._use_neo4j = False

        # Fallback to local graph
        self._graph.add_edge(
            source_id, target_id, relationship=relationship_type, **properties
        )

    def _get_neighbors(self, node_id: str) -> List[str]:
        """Get neighbors from Neo4j if available, otherwise from fallback."""
        if self._use_neo4j and self._ensure_neo4j_connected():
            try:
                async def _get_neighbors():
                    async with self._neo4j_client.driver.session() as session:
                        result = await session.run(
                            "MATCH (n)-[r]->(m) WHERE n.id IS NOT NULL AND n.id = $id RETURN m.id as id",
                            {"id": node_id},
                        )
                        return [record["id"] async for record in result]

                neighbors = self._run_async(_get_neighbors())
                if neighbors is not None:
                    return neighbors
            except Exception as e:
                logger.debug(f"Neo4j neighbors failed: {e}")
                self._use_neo4j = False

        return self._graph.get_neighbors(node_id)

    # ------------------------------------------------------------------
    # Idea operations
    # ------------------------------------------------------------------
    def create_idea(self, text: str, tags: Optional[List[str]] = None, user_id: Optional[str] = None) -> Idea:
        """Create and store a new idea node in the graph.

        Args:
            text: The idea text content
            tags: Optional list of tags for the idea
            user_id: Optional user ID to create relationship from User to Idea

        Returns:
            Created Idea object
        """
        idea_id = str(uuid.uuid4())
        created_at = _utc_now_iso()
        idea = Idea(
            id=idea_id,
            text=text,
            tags=tags or [],
            created_at=created_at,
        )

        self._write_node(
            idea_id,
            label="Idea",
            text=text,
            tags=list(idea.tags),
            created_at=idea.created_at,
            updated_at=idea.updated_at,
        )

        # Create relationship from User to Idea if user_id is provided
        if user_id:
            user_node_id = f"user:{user_id}"
            if self._read_node(user_node_id) is None:
                self._write_node(user_node_id, label="User", user_id=user_id)

            self._create_relationship(
                user_node_id,
                idea_id,
                relationship_type="HAS_IDEA",
                created_at=created_at,
            )
            logger.info("Created idea %s for user %s with HAS_IDEA relationship", idea_id, user_id)
        else:
            logger.info("Created idea %s (no user relationship)", idea_id)

        # Link to similar ideas
        self.link_similar_ideas(idea)

        return idea

    def get_idea(self, idea_id: str) -> Optional[Idea]:
        """Retrieve an idea by ID."""
        data = self._read_node(idea_id)
        if not data or data.get("label") != "Idea":
            return None

        return Idea(
            id=idea_id,
            text=data.get("text", ""),
            tags=list(data.get("tags", []) or []),
            created_at=data.get("created_at", _utc_now_iso()),
            updated_at=data.get("updated_at"),
        )

    def list_ideas(self) -> List[Idea]:
        """List all ideas."""
        # Try Neo4j first
        nodes = self._list_nodes_by_label("Idea")
        if nodes:
            ideas = []
            for node_data in nodes:
                idea_id = node_data.get("id", "")
                ideas.append(
                    Idea(
                        id=idea_id,
                        text=node_data.get("text", ""),
                        tags=list(node_data.get("tags", []) or []),
                        created_at=node_data.get("created_at", _utc_now_iso()),
                        updated_at=node_data.get("updated_at"),
                    )
                )
            return ideas

        # Fallback to local graph
        ideas: List[Idea] = []
        for node_id, data in self._graph.graph.nodes(data=True):
            if data.get("label") != "Idea":
                continue
            ideas.append(
                Idea(
                    id=node_id,
                    text=data.get("text", ""),
                    tags=list(data.get("tags", []) or []),
                    created_at=data.get("created_at", _utc_now_iso()),
                    updated_at=data.get("updated_at"),
                )
            )
        return ideas

    def update_idea(
        self, idea_id: str, text: Optional[str] = None, tags: Optional[List[str]] = None
    ) -> Optional[Idea]:
        """Update an existing idea."""
        logger.debug(f"update_idea called: id={idea_id[:8]}, text={text[:50] if text else None}...")
        
        data = self._read_node(idea_id)
        if not data or data.get("label") != "Idea":
            logger.warning(f"Idea {idea_id[:8]} not found or wrong label")
            return None

        updates: Dict[str, Any] = {}
        if text is not None:
            updates["text"] = text
        if tags is not None:
            updates["tags"] = list(tags)
        updates["updated_at"] = _utc_now_iso()

        logger.info(f"Updating idea {idea_id[:8]} with updates: {updates}")
        
        update_success = self._update_node(idea_id, **updates)
        logger.info(f"Update node result: {update_success}")
        
        idea = self.get_idea(idea_id)
        
        if idea:
            logger.info(f"Retrieved updated idea: {idea.text[:50]}...")
        else:
            logger.error(f"Failed to retrieve idea {idea_id[:8]} after update")

        # Re-link to similar ideas if text or tags changed
        if idea and (text is not None or tags is not None):
            self.link_similar_ideas(idea)

        return idea

    def delete_idea(self, idea_id: str) -> bool:
        """Delete an idea node."""
        return self._delete_node(idea_id)

    def search_ideas(self, query: str) -> List[Idea]:
        """Naive full-text search over idea text and tags."""
        query_lower = query.lower().strip()
        if not query_lower:
            return []

        matches: List[Idea] = []
        for idea in self.list_ideas():
            if query_lower in idea.text.lower() or any(
                query_lower in tag.lower() for tag in idea.tags
            ):
                matches.append(idea)
        return matches

    def find_similar_ideas(self, idea: Idea, threshold: int = 2) -> List[Idea]:
        """Find ideas similar to the given idea based on tags and keywords.

        Args:
            idea: The idea to find similar ideas for
            threshold: Minimum number of matching keywords required

        Returns:
            List of similar ideas (excluding the input idea)
        """
        # Extract significant words from the idea text (4+ chars, lowercase)
        import re
        idea_words = set(
            w.lower() for w in re.findall(r'\b\w{4,}\b', idea.text.lower())
        )
        idea_tags = set(t.lower() for t in (idea.tags or []))

        similar: List[Idea] = []
        for other in self.list_ideas():
            if other.id == idea.id:
                continue

            # Check tag overlap
            other_tags = set(t.lower() for t in (other.tags or []))
            if idea_tags & other_tags:
                similar.append(other)
                continue

            # Check keyword overlap
            other_words = set(
                w.lower() for w in re.findall(r'\b\w{4,}\b', other.text.lower())
            )
            overlap = len(idea_words & other_words)
            if overlap >= threshold:
                similar.append(other)

        return similar

    def link_similar_ideas(self, idea: Idea) -> int:
        """Create RELATED_TO relationships between an idea and similar ideas.

        Args:
            idea: The idea to link

        Returns:
            Number of new connections created
        """
        similar = self.find_similar_ideas(idea)
        connections_created = 0

        for other in similar:
            # Check if relationship already exists (avoid duplicates)
            neighbors = self._get_neighbors(idea.id)
            if other.id not in neighbors:
                self._create_relationship(
                    idea.id,
                    other.id,
                    relationship_type="RELATED_TO",
                    created_at=_utc_now_iso(),
                )
                connections_created += 1
                logger.debug("Linked idea %s to similar idea %s", idea.id[:8], other.id[:8])

        if connections_created > 0:
            logger.info("Created %d connections for idea %s", connections_created, idea.id[:8])

        return connections_created

    # ------------------------------------------------------------------
    # Preference operations (lightweight; can be expanded later)
    # ------------------------------------------------------------------
    def set_preference(
        self,
        user_id: str,
        key: str,
        value: Any,
        strength: float = 1.0,
    ) -> Preference:
        """Create or update a user preference node."""
        # Look for existing preference node
        existing_ids = self._find_nodes(
            label="Preference", user_id=user_id, key=key
        )

        pref_id: str
        created_at: str
        if existing_ids:
            pref_id = existing_ids[0]
            node = self._read_node(pref_id) or {}
            created_at = node.get("created_at", _utc_now_iso())
        else:
            pref_id = str(uuid.uuid4())
            created_at = _utc_now_iso()

        updated_at = _utc_now_iso()
        pref = Preference(
            id=pref_id,
            user_id=user_id,
            key=key,
            value=value,
            strength=float(strength),
            created_at=created_at,
            updated_at=updated_at,
        )

        self._write_node(
            pref_id,
            label="Preference",
            user_id=user_id,
            key=key,
            value=value,
            strength=pref.strength,
            created_at=created_at,
            updated_at=updated_at,
        )

        # Also create relationship from user to preference node
        user_node_id = f"user:{user_id}"
        if self._read_node(user_node_id) is None:
            self._write_node(user_node_id, label="User", user_id=user_id)

        self._create_relationship(
            user_node_id,
            pref_id,
            relationship_type="HAS_PREFERENCE",
        )

        # Invalidate cache for this user
        if user_id in self._preferences_cache:
            del self._preferences_cache[user_id]

        logger.info("Set preference %s for user %s", key, user_id)
        return pref

    def get_preferences(self, user_id: str) -> List[Preference]:
        """Get all preferences for a given user (cached)."""
        # Return cached preferences if available
        if user_id in self._preferences_cache:
            return self._preferences_cache[user_id]

        user_node_id = f"user:{user_id}"
        if self._read_node(user_node_id) is None:
            self._preferences_cache[user_id] = []
            return []

        prefs: List[Preference] = []
        for neighbor_id in self._get_neighbors(user_node_id):
            node = self._read_node(neighbor_id) or {}
            if node.get("label") != "Preference":
                continue
            prefs.append(
                Preference(
                    id=neighbor_id,
                    user_id=node.get("user_id", user_id),
                    key=node.get("key", ""),
                    value=node.get("value"),
                    strength=float(node.get("strength", 1.0)),
                    created_at=node.get("created_at", _utc_now_iso()),
                    updated_at=node.get("updated_at"),
                )
            )

        # Cache the result
        self._preferences_cache[user_id] = prefs
        return prefs

    # ------------------------------------------------------------------
    # Category operations
    # ------------------------------------------------------------------
    def create_category(
        self, name: str, color: str = "#808080", icon: str = "📁"
    ) -> Category:
        """Create a new todo category.

        Args:
            name: Category name
            color: Hex color code (default: gray)
            icon: Unicode emoji icon (default: folder)

        Returns:
            Created Category object
        """
        category_id = str(uuid.uuid4())
        created_at = _utc_now_iso()
        category = Category(
            id=category_id,
            name=name,
            color=color,
            icon=icon,
            created_at=created_at,
        )

        self._write_node(
            category_id,
            label="Category",
            name=name,
            color=color,
            icon=icon,
            created_at=created_at,
        )

        logger.info("Created category %s: %s", category_id, name)
        return category

    def get_category(self, category_id: str) -> Optional[Category]:
        """Retrieve a category by ID."""
        data = self._read_node(category_id)
        if not data or data.get("label") != "Category":
            return None

        return Category(
            id=category_id,
            name=data.get("name", ""),
            color=data.get("color", "#808080"),
            icon=data.get("icon", "📁"),
            created_at=data.get("created_at", _utc_now_iso()),
            updated_at=data.get("updated_at"),
        )

    def list_categories(self) -> List[Category]:
        """List all categories."""
        nodes = self._list_nodes_by_label("Category")
        if nodes:
            categories = []
            for node_data in nodes:
                category_id = node_data.get("id", "")
                categories.append(
                    Category(
                        id=category_id,
                        name=node_data.get("name", ""),
                        color=node_data.get("color", "#808080"),
                        icon=node_data.get("icon", "📁"),
                        created_at=node_data.get("created_at", _utc_now_iso()),
                        updated_at=node_data.get("updated_at"),
                    )
                )
            return categories

        # Fallback to local graph
        categories: List[Category] = []
        for node_id, data in self._graph.graph.nodes(data=True):
            if data.get("label") != "Category":
                continue
            categories.append(
                Category(
                    id=node_id,
                    name=data.get("name", ""),
                    color=data.get("color", "#808080"),
                    icon=data.get("icon", "📁"),
                    created_at=data.get("created_at", _utc_now_iso()),
                    updated_at=data.get("updated_at"),
                )
            )
        return categories

    def update_category(
        self,
        category_id: str,
        name: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> Optional[Category]:
        """Update an existing category."""
        data = self._read_node(category_id)
        if not data or data.get("label") != "Category":
            return None

        updates: Dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if color is not None:
            updates["color"] = color
        if icon is not None:
            updates["icon"] = icon
        updates["updated_at"] = _utc_now_iso()

        self._update_node(category_id, **updates)
        return self.get_category(category_id)

    def delete_category(self, category_id: str) -> bool:
        """Delete a category node."""
        return self._delete_node(category_id)

    # ------------------------------------------------------------------
    # Todo operations
    # ------------------------------------------------------------------
    def create_todo(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        difficulty: int = 3,
        category_id: Optional[str] = None,
        due_date: Optional[str] = None,
        estimated_minutes: Optional[int] = None,
        recurrence_pattern: str = "none",
        parent_todo_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Todo:
        """Create a new todo/task.

        Args:
            title: Todo title
            description: Todo description
            priority: Priority level (low, medium, high, critical)
            difficulty: Difficulty rating (1-5)
            category_id: Optional category ID
            due_date: Optional due date (ISO format)
            estimated_minutes: Estimated time to complete
            recurrence_pattern: Recurrence pattern (none, daily, weekly, monthly)
            parent_todo_id: Optional parent todo ID for subtasks
            user_id: Optional user ID to create relationship

        Returns:
            Created Todo object
        """
        todo_id = str(uuid.uuid4())
        created_at = _utc_now_iso()
        todo = Todo(
            id=todo_id,
            title=title,
            description=description,
            status="todo",
            priority=priority,
            difficulty=difficulty,
            category_id=category_id,
            due_date=due_date,
            estimated_minutes=estimated_minutes,
            recurrence_pattern=recurrence_pattern,
            parent_todo_id=parent_todo_id,
            created_at=created_at,
        )

        self._write_node(
            todo_id,
            label="Todo",
            title=title,
            description=description,
            status="todo",
            priority=priority,
            difficulty=difficulty,
            category_id=category_id or "",
            due_date=due_date or "",
            estimated_minutes=estimated_minutes or 0,
            recurrence_pattern=recurrence_pattern,
            parent_todo_id=parent_todo_id or "",
            created_at=created_at,
        )

        # Create relationship from User to Todo if user_id is provided
        if user_id:
            user_node_id = f"user:{user_id}"
            if self._read_node(user_node_id) is None:
                self._write_node(user_node_id, label="User", user_id=user_id)

            self._create_relationship(
                user_node_id,
                todo_id,
                relationship_type="HAS_TODO",
                created_at=created_at,
            )
            logger.info("Created todo %s for user %s", todo_id, user_id)

        # Create relationship to category if provided
        if category_id:
            self._create_relationship(
                todo_id,
                category_id,
                relationship_type="BELONGS_TO",
                created_at=created_at,
            )

        # Create relationship to parent todo if this is a subtask
        if parent_todo_id:
            self._create_relationship(
                parent_todo_id,
                todo_id,
                relationship_type="HAS_SUBTASK",
                created_at=created_at,
            )

        logger.info("Created todo %s: %s", todo_id, title)
        return todo

    def get_todo(self, todo_id: str) -> Optional[Todo]:
        """Retrieve a todo by ID."""
        data = self._read_node(todo_id)
        if not data or data.get("label") != "Todo":
            return None

        return Todo(
            id=todo_id,
            title=data.get("title", ""),
            description=data.get("description", ""),
            status=data.get("status", "todo"),
            priority=data.get("priority", "medium"),
            difficulty=int(data.get("difficulty", 3)),
            category_id=data.get("category_id") or None,
            due_date=data.get("due_date") or None,
            estimated_minutes=data.get("estimated_minutes") or None,
            recurrence_pattern=data.get("recurrence_pattern", "none"),
            parent_todo_id=data.get("parent_todo_id") or None,
            created_at=data.get("created_at", _utc_now_iso()),
            updated_at=data.get("updated_at"),
            completed_at=data.get("completed_at"),
        )

    def list_todos(
        self,
        status: Optional[str] = None,
        category_id: Optional[str] = None,
        priority: Optional[str] = None,
        parent_todo_id: Optional[str] = None,
    ) -> List[Todo]:
        """List todos with optional filtering.

        Args:
            status: Filter by status (todo, in_progress, completed, cancelled)
            category_id: Filter by category ID
            priority: Filter by priority (low, medium, high, critical)
            parent_todo_id: Filter by parent todo ID (for subtasks)

        Returns:
            List of Todo objects matching filters
        """
        nodes = self._list_nodes_by_label("Todo")
        if nodes:
            todos = []
            for node_data in nodes:
                todo_id = node_data.get("id", "")
                todo = Todo(
                    id=todo_id,
                    title=node_data.get("title", ""),
                    description=node_data.get("description", ""),
                    status=node_data.get("status", "todo"),
                    priority=node_data.get("priority", "medium"),
                    difficulty=int(node_data.get("difficulty", 3)),
                    category_id=node_data.get("category_id") or None,
                    due_date=node_data.get("due_date") or None,
                    estimated_minutes=node_data.get("estimated_minutes") or None,
                    recurrence_pattern=node_data.get("recurrence_pattern", "none"),
                    parent_todo_id=node_data.get("parent_todo_id") or None,
                    created_at=node_data.get("created_at", _utc_now_iso()),
                    updated_at=node_data.get("updated_at"),
                    completed_at=node_data.get("completed_at"),
                )
                # Apply filters
                if status and todo.status != status:
                    continue
                if category_id and todo.category_id != category_id:
                    continue
                if priority and todo.priority != priority:
                    continue
                if parent_todo_id is not None and todo.parent_todo_id != parent_todo_id:
                    continue
                todos.append(todo)
            return todos

        # Fallback to local graph
        todos: List[Todo] = []
        for node_id, data in self._graph.graph.nodes(data=True):
            if data.get("label") != "Todo":
                continue
            todo = Todo(
                id=node_id,
                title=data.get("title", ""),
                description=data.get("description", ""),
                status=data.get("status", "todo"),
                priority=data.get("priority", "medium"),
                difficulty=int(data.get("difficulty", 3)),
                category_id=data.get("category_id") or None,
                due_date=data.get("due_date") or None,
                estimated_minutes=data.get("estimated_minutes") or None,
                recurrence_pattern=data.get("recurrence_pattern", "none"),
                parent_todo_id=data.get("parent_todo_id") or None,
                created_at=data.get("created_at", _utc_now_iso()),
                updated_at=data.get("updated_at"),
                completed_at=data.get("completed_at"),
            )
            # Apply filters
            if status and todo.status != status:
                continue
            if category_id and todo.category_id != category_id:
                continue
            if priority and todo.priority != priority:
                continue
            if parent_todo_id is not None and todo.parent_todo_id != parent_todo_id:
                continue
            todos.append(todo)
        return todos

    def update_todo(
        self,
        todo_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        difficulty: Optional[int] = None,
        category_id: Optional[str] = None,
        due_date: Optional[str] = None,
        estimated_minutes: Optional[int] = None,
        recurrence_pattern: Optional[str] = None,
        completed_at: Optional[str] = None,
    ) -> Optional[Todo]:
        """Update an existing todo."""
        data = self._read_node(todo_id)
        if not data or data.get("label") != "Todo":
            return None

        updates: Dict[str, Any] = {}
        if title is not None:
            updates["title"] = title
        if description is not None:
            updates["description"] = description
        if status is not None:
            updates["status"] = status
            # Set completed_at when marking as completed
            if status == "completed" and completed_at is None:
                updates["completed_at"] = _utc_now_iso()
        if priority is not None:
            updates["priority"] = priority
        if difficulty is not None:
            updates["difficulty"] = difficulty
        if category_id is not None:
            updates["category_id"] = category_id
        if due_date is not None:
            updates["due_date"] = due_date
        if estimated_minutes is not None:
            updates["estimated_minutes"] = estimated_minutes
        if recurrence_pattern is not None:
            updates["recurrence_pattern"] = recurrence_pattern
        if completed_at is not None:
            updates["completed_at"] = completed_at
        updates["updated_at"] = _utc_now_iso()

        self._update_node(todo_id, **updates)
        return self.get_todo(todo_id)

    def delete_todo(self, todo_id: str) -> bool:
        """Delete a todo node."""
        return self._delete_node(todo_id)

    def get_todos_by_category(self, category_id: str) -> List[Todo]:
        """Get all todos in a specific category."""
        return self.list_todos(category_id=category_id)

    def get_todos_by_status(self, status: str) -> List[Todo]:
        """Get all todos with a specific status."""
        return self.list_todos(status=status)

    def link_todo_to_idea(self, todo_id: str, idea_id: str) -> bool:
        """Create an IMPLEMENTS relationship from todo to idea.

        Args:
            todo_id: The todo ID
            idea_id: The idea ID

        Returns:
            True if link was created successfully
        """
        # Verify both nodes exist
        todo = self.get_todo(todo_id)
        idea = self.get_idea(idea_id)
        if not todo or not idea:
            return False

        self._create_relationship(
            todo_id,
            idea_id,
            relationship_type="IMPLEMENTS",
            created_at=_utc_now_iso(),
        )
        logger.info("Linked todo %s to idea %s", todo_id, idea_id)
        return True

    def add_todo_dependency(self, todo_id: str, depends_on_id: str) -> bool:
        """Create a DEPENDS_ON relationship between todos.

        Args:
            todo_id: The dependent todo ID
            depends_on_id: The todo this one depends on

        Returns:
            True if dependency was created successfully
        """
        # Verify both nodes exist
        todo = self.get_todo(todo_id)
        depends_on = self.get_todo(depends_on_id)
        if not todo or not depends_on:
            return False

        self._create_relationship(
            todo_id,
            depends_on_id,
            relationship_type="DEPENDS_ON",
            created_at=_utc_now_iso(),
        )
        logger.info("Added dependency: todo %s depends on %s", todo_id, depends_on_id)
        return True

    def get_subtasks(self, parent_todo_id: str) -> List[Todo]:
        """Get all subtasks for a given parent todo.

        Args:
            parent_todo_id: The parent todo ID

        Returns:
            List of subtask Todo objects
        """
        return self.list_todos(parent_todo_id=parent_todo_id)

    def check_and_create_recurring_todos(self, user_id: Optional[str] = None) -> List[Todo]:
        """Check for recurring todos and create new instances as needed.

        This should be called daily or on app startup to generate todo instances
        based on recurrence patterns.

        Args:
            user_id: Optional user ID to filter recurring todos

        Returns:
            List of newly created todo instances
        """
        from datetime import datetime, timedelta, timezone

        # Get all todos with recurrence patterns
        all_todos = self.list_todos()
        recurring_todos = [t for t in all_todos if t.recurrence_pattern != "none"]

        created_todos = []
        now = datetime.now(timezone.utc)

        for template in recurring_todos:
            # Skip if not for this user (if user_id specified)
            if user_id:
                # Check if this todo belongs to the user
                user_node_id = f"user:{user_id}"
                if user_node_id not in self._get_neighbors(template.id):
                    continue

            # Determine if we need to create a new instance
            # Check if there's already a non-completed instance created recently
            last_created = template.created_at
            if template.updated_at:
                last_created = template.updated_at

            try:
                last_created_dt = datetime.fromisoformat(last_created.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                last_created_dt = datetime.now(timezone.utc) - timedelta(days=1)

            should_create = False
            if template.recurrence_pattern == "daily":
                # Create if last created was yesterday or earlier
                if (now - last_created_dt).days >= 1:
                    should_create = True
            elif template.recurrence_pattern == "weekly":
                # Create if last created was a week or more ago
                if (now - last_created_dt).days >= 7:
                    should_create = True
            elif template.recurrence_pattern == "monthly":
                # Create if last created was a month or more ago
                if (now - last_created_dt).days >= 30:
                    should_create = True

            if should_create:
                # Create new todo instance based on template
                new_todo = self.create_todo(
                    title=template.title,
                    description=template.description,
                    priority=template.priority,
                    difficulty=template.difficulty,
                    category_id=template.category_id,
                    due_date=None,  # Calculate new due date based on recurrence
                    estimated_minutes=template.estimated_minutes,
                    recurrence_pattern="none",  # Individual instances don't recur
                    parent_todo_id=None,
                    user_id=user_id,
                )

                # Link to original recurring todo template
                self._create_relationship(
                    new_todo.id,
                    template.id,
                    relationship_type="INSTANCE_OF",
                    created_at=_utc_now_iso(),
                )

                created_todos.append(new_todo)
                logger.info(
                    f"Created recurring todo instance: {new_todo.title} (from template {template.id})"
                )

                # Update template's updated_at to track last generation
                self.update_todo(template.id, updated_at=_utc_now_iso())

        return created_todos

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    @staticmethod
    def idea_to_dict(idea: Idea) -> Dict[str, Any]:
        """Convert Idea dataclass to plain dict (for API responses)."""
        return asdict(idea)

    @staticmethod
    def preference_to_dict(pref: Preference) -> Dict[str, Any]:
        """Convert Preference dataclass to plain dict."""
        return asdict(pref)

    @staticmethod
    def category_to_dict(category: Category) -> Dict[str, Any]:
        """Convert Category dataclass to plain dict."""
        return asdict(category)

    @staticmethod
    def todo_to_dict(todo: Todo) -> Dict[str, Any]:
        """Convert Todo dataclass to plain dict."""
        return asdict(todo)


__all__ = [
    "KnowledgeService",
    "Idea",
    "Preference",
    "Category",
    "Todo",
]
