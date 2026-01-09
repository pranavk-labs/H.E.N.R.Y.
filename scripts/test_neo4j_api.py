#!/usr/bin/env python3
"""Test script for Neo4j connection and Graph API endpoints.

Usage:
    # Test Neo4j connection and health
    poetry run python scripts/test_neo4j_api.py --health

    # Test Graph API endpoints (requires API server running)
    poetry run python scripts/test_neo4j_api.py --api

    # Test direct Neo4j operations
    poetry run python scripts/test_neo4j_api.py --direct

    # Run all tests
    poetry run python scripts/test_neo4j_api.py --all
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.neo4j_client import Neo4jClient
from backend.config.settings import get_settings


async def test_neo4j_health():
    """Test Neo4j connection and health check."""
    print("=" * 60)
    print("Testing Neo4j Connection")
    print("=" * 60)
    print()

    settings = get_settings()
    print(f"Neo4j URI: {settings.neo4j_uri}")
    print(f"Neo4j User: {settings.neo4j_user}")
    print()

    client = Neo4jClient.get_instance()
    
    try:
        print("Connecting to Neo4j...")
        await client.connect()
        print("✓ Successfully connected to Neo4j")
        print()

        print("Running health check...")
        health = await client.health_check()
        
        if health["status"] == "healthy":
            print("✓ Neo4j is healthy")
            print(f"  Connected: {health.get('connected', False)}")
            print(f"  URI: {health.get('uri', 'N/A')}")
        else:
            print("✗ Neo4j health check failed")
            print(f"  Error: {health.get('error', 'Unknown error')}")
            return False

        print()
        print("Testing basic query...")
        async with client.driver.session() as session:
            result = await session.run("RETURN 'Hello from Neo4j!' as message")
            record = await result.single()
            if record:
                print(f"✓ Query successful: {record['message']}")
            else:
                print("✗ Query returned no results")
                return False

        print()
        print("=" * 60)
        print("Neo4j connection test: PASSED")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"✗ Failed to connect to Neo4j: {e}")
        print()
        print("Make sure Neo4j is running in Docker:")
        print("  docker run -d --name neo4j \\")
        print("    -p 7474:7474 -p 7687:7687 \\")
        print("    -e NEO4J_AUTH=neo4j/password \\")
        print("    neo4j:latest")
        return False
    finally:
        await client.disconnect()


async def test_direct_neo4j_operations():
    """Test direct Neo4j operations (create nodes, relationships, queries)."""
    print("=" * 60)
    print("Testing Direct Neo4j Operations")
    print("=" * 60)
    print()

    client = Neo4jClient.get_instance()
    
    try:
        await client.connect()
        print("✓ Connected to Neo4j")
        print()

        async with client.driver.session() as session:
            # Clear test data
            print("Cleaning up any existing test data...")
            await session.run("MATCH (n:TestNode) DELETE n")
            print("✓ Cleaned up")
            print()

            # Create a test node
            print("Creating test nodes...")
            result = await session.run(
                """
                CREATE (u:TestNode {id: 'user', name: 'Test User', role: 'user'})
                CREATE (h:TestNode {id: 'henry', name: 'HENRY', role: 'assistant'})
                RETURN u, h
                """
            )
            await result.consume()
            print("✓ Created 2 test nodes")
            print()

            # Create a relationship
            print("Creating relationship...")
            result = await session.run(
                """
                MATCH (u:TestNode {id: 'user'})
                MATCH (h:TestNode {id: 'henry'})
                CREATE (u)-[:USES {since: '2024'}]->(h)
                RETURN u, h
                """
            )
            await result.consume()
            print("✓ Created relationship")
            print()

            # Query nodes
            print("Querying nodes...")
            result = await session.run(
                "MATCH (n:TestNode) RETURN n.id as id, n.name as name, n.role as role"
            )
            nodes = [record async for record in result]
            print(f"✓ Found {len(nodes)} nodes:")
            for node in nodes:
                print(f"  - {node['id']}: {node['name']} ({node['role']})")
            print()

            # Query relationships
            print("Querying relationships...")
            result = await session.run(
                """
                MATCH (u:TestNode)-[r:USES]->(h:TestNode)
                RETURN u.id as source, type(r) as rel, h.id as target, r.since as since
                """
            )
            relationships = [record async for record in result]
            print(f"✓ Found {len(relationships)} relationships:")
            for rel in relationships:
                print(f"  - {rel['source']} --[{rel['rel']}]--> {rel['target']} (since: {rel['since']})")
            print()

            # Clean up
            print("Cleaning up test data...")
            await session.run("MATCH (n:TestNode) DETACH DELETE n")
            print("✓ Cleaned up")
            print()

        print("=" * 60)
        print("Direct Neo4j operations test: PASSED")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.disconnect()


async def test_graph_api(base_url: str = "http://localhost:8000"):
    """Test Graph API endpoints via HTTP."""
    print("=" * 60)
    print("Testing Graph API Endpoints")
    print("=" * 60)
    print()

    try:
        import httpx
    except ImportError:
        print("✗ httpx not installed. Install with: poetry add httpx")
        return False

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        # Test health endpoint
        print("Testing health endpoint...")
        try:
            response = await client.get("/health")
            response.raise_for_status()
            health_data = response.json()
            print("✓ Health endpoint responded")
            print(f"  Overall status: {health_data.get('status')}")
            neo4j_status = health_data.get('services', {}).get('neo4j', {})
            print(f"  Neo4j status: {neo4j_status.get('status')}")
            if neo4j_status.get('status') != 'healthy':
                print(f"  ⚠ Warning: Neo4j is not healthy: {neo4j_status.get('error', 'Unknown')}")
            print()
        except httpx.ConnectError:
            print("✗ Cannot connect to API server")
            print(f"  Make sure the server is running at {base_url}")
            print("  Start with: poetry run python scripts/dev_server.py")
            return False
        except Exception as e:
            print(f"✗ Health check failed: {e}")
            return False

        # Test graph stats
        print("Testing GET /graph/stats...")
        try:
            response = await client.get("/graph/stats")
            response.raise_for_status()
            stats = response.json()
            print(f"✓ Graph stats: {stats.get('nodes')} nodes, {stats.get('edges')} edges")
            print()
        except Exception as e:
            print(f"✗ Failed: {e}")
            return False

        # Test creating nodes
        print("Testing POST /graph/nodes...")
        try:
            # Create user node
            response = await client.post(
                "/graph/nodes",
                json={
                    "node_id": "test_user",
                    "label": "Person",
                    "properties": {"name": "Test User", "role": "user"}
                }
            )
            response.raise_for_status()
            print("✓ Created user node")
            
            # Create assistant node
            response = await client.post(
                "/graph/nodes",
                json={
                    "node_id": "test_henry",
                    "label": "Assistant",
                    "properties": {"name": "HENRY", "role": "assistant"}
                }
            )
            response.raise_for_status()
            print("✓ Created assistant node")
            print()
        except Exception as e:
            print(f"✗ Failed to create nodes: {e}")
            return False

        # Test getting a node
        print("Testing GET /graph/nodes/{node_id}...")
        try:
            response = await client.get("/graph/nodes/test_user")
            response.raise_for_status()
            node_data = response.json()
            print(f"✓ Retrieved node: {node_data.get('node_id')}")
            print(f"  Data: {node_data.get('data')}")
            print()
        except Exception as e:
            print(f"✗ Failed: {e}")
            return False

        # Test listing nodes
        print("Testing GET /graph/nodes...")
        try:
            response = await client.get("/graph/nodes")
            response.raise_for_status()
            nodes_data = response.json()
            node_count = len(nodes_data.get('nodes', {}))
            print(f"✓ Listed {node_count} nodes")
            print()
        except Exception as e:
            print(f"✗ Failed: {e}")
            return False

        # Test finding nodes
        print("Testing POST /graph/nodes/find...")
        try:
            response = await client.post(
                "/graph/nodes/find",
                json={"label": "Person", "properties": {}}
            )
            response.raise_for_status()
            find_data = response.json()
            print(f"✓ Found {find_data.get('count')} matching nodes")
            print()
        except Exception as e:
            print(f"✗ Failed: {e}")
            return False

        # Test creating an edge
        print("Testing POST /graph/edges...")
        try:
            response = await client.post(
                "/graph/edges",
                json={
                    "source": "test_user",
                    "target": "test_henry",
                    "relationship": "USES",
                    "properties": {"since": "2024"}
                }
            )
            response.raise_for_status()
            print("✓ Created edge")
            print()
        except Exception as e:
            print(f"✗ Failed: {e}")
            return False

        # Test getting neighbors
        print("Testing GET /graph/nodes/{node_id}/neighbors...")
        try:
            response = await client.get("/graph/nodes/test_user/neighbors")
            response.raise_for_status()
            neighbors_data = response.json()
            print(f"✓ Found {neighbors_data.get('count')} neighbors")
            print()
        except Exception as e:
            print(f"✗ Failed: {e}")
            return False

        # Test deleting nodes
        print("Testing DELETE /graph/nodes/{node_id}...")
        try:
            response = await client.delete("/graph/nodes/test_user")
            response.raise_for_status()
            print("✓ Deleted user node")
            
            response = await client.delete("/graph/nodes/test_henry")
            response.raise_for_status()
            print("✓ Deleted assistant node")
            print()
        except Exception as e:
            print(f"✗ Failed: {e}")
            return False

        # Final stats
        print("Final graph stats...")
        try:
            response = await client.get("/graph/stats")
            response.raise_for_status()
            stats = response.json()
            print(f"✓ Final stats: {stats.get('nodes')} nodes, {stats.get('edges')} edges")
            print()
        except Exception as e:
            print(f"✗ Failed: {e}")
            return False

    print("=" * 60)
    print("Graph API endpoints test: PASSED")
    print("=" * 60)
    return True


async def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test Neo4j connection and Graph API")
    parser.add_argument(
        "--health",
        action="store_true",
        help="Test Neo4j connection and health check"
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Test direct Neo4j operations"
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="Test Graph API endpoints (requires API server running)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )

    args = parser.parse_args()

    if not any([args.health, args.direct, args.api, args.all]):
        parser.print_help()
        return

    results = []

    if args.health or args.all:
        result = await test_neo4j_health()
        results.append(("Neo4j Health", result))
        print()

    if args.direct or args.all:
        result = await test_direct_neo4j_operations()
        results.append(("Direct Neo4j Operations", result))
        print()

    if args.api or args.all:
        result = await test_graph_api(args.api_url)
        results.append(("Graph API", result))
        print()

    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
    print("=" * 60)

    # Exit with error code if any test failed
    if not all(result[1] for result in results):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

