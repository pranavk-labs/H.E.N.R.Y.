#!/usr/bin/env python3
"""
Standalone script to populate Neo4j test database with comprehensive sample data.

This script creates all node types and relationships used in H.E.N.R.Y.'s lifecycle
without requiring pytest. Useful for manual testing and database exploration.

Usage:
    python scripts/populate_test_db.py

Environment variables:
    NEO4J_URI - Neo4j connection URI (default: bolt://localhost:7687)
    NEO4J_USER - Neo4j username (default: neo4j)
    NEO4J_PASSWORD - Neo4j password (required)
    NEO4J_DATABASE - Database name (default: henrytest)
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.neo4j_client import Neo4jClient
from backend.config.settings import Settings


async def populate_database():
    """Populate the test database with comprehensive sample data."""

    # Configuration
    settings = Settings()
    settings.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    settings.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    settings.neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    db_name = os.getenv("NEO4J_DATABASE", "neo4j")  # Community Edition default

    if not settings.neo4j_password:
        print("Error: NEO4J_PASSWORD environment variable is required")
        print("\nUsage:")
        print("  export NEO4J_PASSWORD='your_password'")
        print("  python scripts/populate_test_db.py")
        sys.exit(1)

    print(f"Connecting to Neo4j at {settings.neo4j_uri}")
    print(f"Using database: {db_name}")
    print()

    # Reset instance and create new client
    Neo4jClient._instance = None
    Neo4jClient._driver = None
    client = Neo4jClient(settings)

    try:
        await client.connect()
        print("✓ Connected to Neo4j")
        print()

        async with client.driver.session(database=db_name) as session:
            # Clear existing test data
            print("Clearing existing data...")
            await session.run("MATCH (n) DETACH DELETE n")
            print("✓ Database cleared")
            print()

            # Get current timestamp
            now = datetime.now(timezone.utc).isoformat()

            print("Creating nodes and relationships...")
            print("=" * 60)

            # ================================================================
            # 1. Create User node
            # ================================================================
            user_id = "user:test_user_001"
            await session.run(
                """
                CREATE (u:User {
                    id: $id,
                    user_id: $user_id,
                    created_at: $created_at
                })
                """,
                id=user_id,
                user_id="test_user_001",
                created_at=now
            )
            print(f"✓ Created User node: {user_id}")

            # ================================================================
            # 2. Create Preference node with HAS_PREFERENCE relationship
            # ================================================================
            pref_id = "pref:test_user_001:favorite_color"
            await session.run(
                """
                CREATE (p:Preference {
                    id: $id,
                    user_id: $user_id,
                    key: $key,
                    value: $value,
                    strength: $strength,
                    created_at: $created_at
                })
                """,
                id=pref_id,
                user_id="test_user_001",
                key="favorite_color",
                value="blue",
                strength=0.9,
                created_at=now
            )

            await session.run(
                """
                MATCH (u:User {id: $user_id})
                MATCH (p:Preference {id: $pref_id})
                CREATE (u)-[r:HAS_PREFERENCE {created_at: $created_at}]->(p)
                """,
                user_id=user_id,
                pref_id=pref_id,
                created_at=now
            )
            print(f"✓ Created Preference node: {pref_id}")
            print(f"  └─ HAS_PREFERENCE: {user_id} -> {pref_id}")

            # ================================================================
            # 3. Create Idea nodes with HAS_IDEA and RELATED_TO relationships
            # ================================================================
            idea1_id = "idea:build_robot_arm"
            await session.run(
                """
                CREATE (i:Idea {
                    id: $id,
                    text: $text,
                    tags: $tags,
                    user_id: $user_id,
                    created_at: $created_at
                })
                """,
                id=idea1_id,
                text="Build a 3-DOF robot arm for desktop assistance",
                tags=["robotics", "hardware", "automation"],
                user_id="test_user_001",
                created_at=now
            )

            await session.run(
                """
                MATCH (u:User {id: $user_id})
                MATCH (i:Idea {id: $idea_id})
                CREATE (u)-[r:HAS_IDEA {created_at: $created_at}]->(i)
                """,
                user_id=user_id,
                idea_id=idea1_id,
                created_at=now
            )
            print(f"✓ Created Idea node: {idea1_id}")
            print(f"  └─ HAS_IDEA: {user_id} -> {idea1_id}")

            idea2_id = "idea:learn_inverse_kinematics"
            await session.run(
                """
                CREATE (i:Idea {
                    id: $id,
                    text: $text,
                    tags: $tags,
                    user_id: $user_id,
                    created_at: $created_at
                })
                """,
                id=idea2_id,
                text="Learn inverse kinematics algorithms for robot control",
                tags=["robotics", "mathematics", "learning"],
                user_id="test_user_001",
                created_at=now
            )

            await session.run(
                """
                MATCH (u:User {id: $user_id})
                MATCH (i:Idea {id: $idea_id})
                CREATE (u)-[r:HAS_IDEA {created_at: $created_at}]->(i)
                """,
                user_id=user_id,
                idea_id=idea2_id,
                created_at=now
            )

            await session.run(
                """
                MATCH (i1:Idea {id: $idea1_id})
                MATCH (i2:Idea {id: $idea2_id})
                CREATE (i1)-[r:RELATED_TO {
                    reason: $reason,
                    created_at: $created_at
                }]->(i2)
                """,
                idea1_id=idea1_id,
                idea2_id=idea2_id,
                reason="IK needed for robot arm control",
                created_at=now
            )
            print(f"✓ Created Idea node: {idea2_id}")
            print(f"  └─ HAS_IDEA: {user_id} -> {idea2_id}")
            print(f"  └─ RELATED_TO: {idea1_id} -> {idea2_id}")

            # ================================================================
            # 4. Create Category node
            # ================================================================
            category_id = "category:learning"
            await session.run(
                """
                CREATE (c:Category {
                    id: $id,
                    name: $name,
                    color: $color,
                    icon: $icon,
                    created_at: $created_at
                })
                """,
                id=category_id,
                name="Learning",
                color="#4CAF50",
                icon="📚",
                created_at=now
            )
            print(f"✓ Created Category node: {category_id}")

            # ================================================================
            # 5. Create Todo nodes with multiple relationship types
            # ================================================================
            todo1_id = "todo:study_robotics"
            await session.run(
                """
                CREATE (t:Todo {
                    id: $id,
                    title: $title,
                    description: $description,
                    status: $status,
                    priority: $priority,
                    difficulty: $difficulty,
                    category_id: $category_id,
                    due_date: $due_date,
                    estimated_minutes: $estimated_minutes,
                    recurrence_pattern: $recurrence_pattern,
                    created_at: $created_at
                })
                """,
                id=todo1_id,
                title="Study robotics fundamentals",
                description="Complete online course on robotics basics",
                status="in_progress",
                priority="high",
                difficulty=3,
                category_id=category_id,
                due_date="2026-02-01T00:00:00Z",
                estimated_minutes=180,
                recurrence_pattern="none",
                created_at=now
            )

            await session.run(
                """
                MATCH (u:User {id: $user_id})
                MATCH (t:Todo {id: $todo_id})
                CREATE (u)-[r:HAS_TODO {created_at: $created_at}]->(t)
                """,
                user_id=user_id,
                todo_id=todo1_id,
                created_at=now
            )

            await session.run(
                """
                MATCH (t:Todo {id: $todo_id})
                MATCH (c:Category {id: $category_id})
                CREATE (t)-[r:BELONGS_TO {created_at: $created_at}]->(c)
                """,
                todo_id=todo1_id,
                category_id=category_id,
                created_at=now
            )

            await session.run(
                """
                MATCH (t:Todo {id: $todo_id})
                MATCH (i:Idea {id: $idea_id})
                CREATE (t)-[r:IMPLEMENTS {created_at: $created_at}]->(i)
                """,
                todo_id=todo1_id,
                idea_id=idea2_id,
                created_at=now
            )

            print(f"✓ Created Todo node: {todo1_id}")
            print(f"  └─ HAS_TODO: {user_id} -> {todo1_id}")
            print(f"  └─ BELONGS_TO: {todo1_id} -> {category_id}")
            print(f"  └─ IMPLEMENTS: {todo1_id} -> {idea2_id}")

            todo2_id = "todo:read_robotics_chapter_1"
            await session.run(
                """
                CREATE (t:Todo {
                    id: $id,
                    title: $title,
                    description: $description,
                    status: $status,
                    priority: $priority,
                    difficulty: $difficulty,
                    category_id: $category_id,
                    parent_todo_id: $parent_todo_id,
                    estimated_minutes: $estimated_minutes,
                    recurrence_pattern: $recurrence_pattern,
                    created_at: $created_at
                })
                """,
                id=todo2_id,
                title="Read Chapter 1: Introduction to Robotics",
                description="Read and take notes on the first chapter",
                status="todo",
                priority="medium",
                difficulty=2,
                category_id=category_id,
                parent_todo_id=todo1_id,
                estimated_minutes=45,
                recurrence_pattern="none",
                created_at=now
            )

            await session.run(
                """
                MATCH (u:User {id: $user_id})
                MATCH (t:Todo {id: $todo_id})
                CREATE (u)-[r:HAS_TODO {created_at: $created_at}]->(t)
                """,
                user_id=user_id,
                todo_id=todo2_id,
                created_at=now
            )

            await session.run(
                """
                MATCH (t:Todo {id: $todo_id})
                MATCH (c:Category {id: $category_id})
                CREATE (t)-[r:BELONGS_TO {created_at: $created_at}]->(c)
                """,
                todo_id=todo2_id,
                category_id=category_id,
                created_at=now
            )

            await session.run(
                """
                MATCH (parent:Todo {id: $parent_id})
                MATCH (child:Todo {id: $child_id})
                CREATE (parent)-[r:HAS_SUBTASK {created_at: $created_at}]->(child)
                """,
                parent_id=todo1_id,
                child_id=todo2_id,
                created_at=now
            )

            print(f"✓ Created Todo node: {todo2_id}")
            print(f"  └─ HAS_TODO: {user_id} -> {todo2_id}")
            print(f"  └─ BELONGS_TO: {todo2_id} -> {category_id}")
            print(f"  └─ HAS_SUBTASK: {todo1_id} -> {todo2_id}")

            todo3_id = "todo:practice_ik_examples"
            await session.run(
                """
                CREATE (t:Todo {
                    id: $id,
                    title: $title,
                    description: $description,
                    status: $status,
                    priority: $priority,
                    difficulty: $difficulty,
                    category_id: $category_id,
                    estimated_minutes: $estimated_minutes,
                    recurrence_pattern: $recurrence_pattern,
                    created_at: $created_at
                })
                """,
                id=todo3_id,
                title="Practice inverse kinematics examples",
                description="Work through 5 IK problem sets",
                status="todo",
                priority="medium",
                difficulty=4,
                category_id=category_id,
                estimated_minutes=120,
                recurrence_pattern="none",
                created_at=now
            )

            await session.run(
                """
                MATCH (u:User {id: $user_id})
                MATCH (t:Todo {id: $todo_id})
                CREATE (u)-[r:HAS_TODO {created_at: $created_at}]->(t)
                """,
                user_id=user_id,
                todo_id=todo3_id,
                created_at=now
            )

            await session.run(
                """
                MATCH (t:Todo {id: $todo_id})
                MATCH (c:Category {id: $category_id})
                CREATE (t)-[r:BELONGS_TO {created_at: $created_at}]->(c)
                """,
                todo_id=todo3_id,
                category_id=category_id,
                created_at=now
            )

            await session.run(
                """
                MATCH (dependent:Todo {id: $dependent_id})
                MATCH (dependency:Todo {id: $dependency_id})
                CREATE (dependent)-[r:DEPENDS_ON {created_at: $created_at}]->(dependency)
                """,
                dependent_id=todo3_id,
                dependency_id=todo1_id,
                created_at=now
            )

            print(f"✓ Created Todo node: {todo3_id}")
            print(f"  └─ HAS_TODO: {user_id} -> {todo3_id}")
            print(f"  └─ BELONGS_TO: {todo3_id} -> {category_id}")
            print(f"  └─ DEPENDS_ON: {todo3_id} -> {todo1_id}")

            # ================================================================
            # 6. Create CalendarEvent nodes (template and instance)
            # ================================================================
            event_template_id = "event:weekly_robotics_seminar"
            await session.run(
                """
                CREATE (e:CalendarEvent {
                    id: $id,
                    title: $title,
                    start_time: $start_time,
                    end_time: $end_time,
                    description: $description,
                    location: $location,
                    recurrence_pattern: $recurrence_pattern,
                    recurrence_end_date: $recurrence_end_date,
                    reminder_minutes: $reminder_minutes,
                    attendees: $attendees,
                    event_type: $event_type,
                    status: $status,
                    created_at: $created_at
                })
                """,
                id=event_template_id,
                title="Weekly Robotics Seminar",
                start_time="2026-01-20T14:00:00Z",
                end_time="2026-01-20T15:30:00Z",
                description="Weekly discussion on robotics research and projects",
                location="Engineering Building Room 301",
                recurrence_pattern="weekly",
                recurrence_end_date="2026-05-01T00:00:00Z",
                reminder_minutes=30,
                attendees=["alice@example.com", "bob@example.com"],
                event_type="meeting",
                status="scheduled",
                created_at=now
            )

            await session.run(
                """
                MATCH (u:User {id: $user_id})
                MATCH (e:CalendarEvent {id: $event_id})
                CREATE (u)-[r:HAS_EVENT {created_at: $created_at}]->(e)
                """,
                user_id=user_id,
                event_id=event_template_id,
                created_at=now
            )

            print(f"✓ Created CalendarEvent (template): {event_template_id}")
            print(f"  └─ HAS_EVENT: {user_id} -> {event_template_id}")

            event_instance_id = "event:weekly_robotics_seminar_2026_01_27"
            await session.run(
                """
                CREATE (e:CalendarEvent {
                    id: $id,
                    title: $title,
                    start_time: $start_time,
                    end_time: $end_time,
                    description: $description,
                    location: $location,
                    recurrence_pattern: $recurrence_pattern,
                    reminder_minutes: $reminder_minutes,
                    attendees: $attendees,
                    event_type: $event_type,
                    status: $status,
                    created_at: $created_at
                })
                """,
                id=event_instance_id,
                title="Weekly Robotics Seminar",
                start_time="2026-01-27T14:00:00Z",
                end_time="2026-01-27T15:30:00Z",
                description="Weekly discussion on robotics research and projects",
                location="Engineering Building Room 301",
                recurrence_pattern="none",
                reminder_minutes=30,
                attendees=["alice@example.com", "bob@example.com"],
                event_type="meeting",
                status="scheduled",
                created_at=now
            )

            await session.run(
                """
                MATCH (instance:CalendarEvent {id: $instance_id})
                MATCH (template:CalendarEvent {id: $template_id})
                CREATE (instance)-[r:INSTANCE_OF {created_at: $created_at}]->(template)
                """,
                instance_id=event_instance_id,
                template_id=event_template_id,
                created_at=now
            )

            await session.run(
                """
                MATCH (u:User {id: $user_id})
                MATCH (e:CalendarEvent {id: $event_id})
                CREATE (u)-[r:HAS_EVENT {created_at: $created_at}]->(e)
                """,
                user_id=user_id,
                event_id=event_instance_id,
                created_at=now
            )

            print(f"✓ Created CalendarEvent (instance): {event_instance_id}")
            print(f"  └─ INSTANCE_OF: {event_instance_id} -> {event_template_id}")
            print(f"  └─ HAS_EVENT: {user_id} -> {event_instance_id}")

            # ================================================================
            # Verify the graph
            # ================================================================
            result = await session.run("MATCH (n) RETURN count(n) as node_count")
            record = await result.single()
            node_count = record["node_count"]

            result = await session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
            record = await result.single()
            rel_count = record["rel_count"]

            print()
            print("=" * 60)
            print("Graph populated successfully!")
            print("=" * 60)
            print(f"Total nodes created: {node_count}")
            print(f"Total relationships created: {rel_count}")
            print()
            print("Node summary:")
            print("  - 1 User")
            print("  - 1 Preference")
            print("  - 2 Ideas")
            print("  - 1 Category")
            print("  - 3 Todos")
            print("  - 2 CalendarEvents (1 template + 1 instance)")
            print()
            print("Relationship summary:")
            print("  - HAS_PREFERENCE: 1")
            print("  - HAS_IDEA: 2")
            print("  - RELATED_TO: 1")
            print("  - HAS_TODO: 3")
            print("  - BELONGS_TO: 3")
            print("  - IMPLEMENTS: 1")
            print("  - HAS_SUBTASK: 1")
            print("  - DEPENDS_ON: 1")
            print("  - HAS_EVENT: 2")
            print("  - INSTANCE_OF: 1")
            print("=" * 60)
            print()
            print(f"View in Neo4j Browser:")
            print(f"  1. Navigate to http://localhost:7474")
            print(f"  2. Run: :use {db_name}")
            print(f"  3. Run: MATCH (n)-[r]->(m) RETURN n, r, m;")
            print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await client.disconnect()
        print("✓ Disconnected from Neo4j")


if __name__ == "__main__":
    asyncio.run(populate_database())
