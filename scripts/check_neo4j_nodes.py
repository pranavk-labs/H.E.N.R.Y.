#!/usr/bin/env python3
"""Quick script to check what nodes exist in Neo4j.

Run with: poetry run python scripts/check_neo4j_nodes.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.neo4j_client import Neo4jClient


async def check_nodes():
    """Check nodes in Neo4j."""
    client = Neo4jClient.get_instance()
    
    try:
        await client.connect()
        print("✓ Connected to Neo4j\n")
        
        async with client.driver.session() as session:
            # Count all nodes
            result = await session.run("MATCH (n) RETURN count(n) as count")
            record = await result.single()
            total_nodes = record["count"] if record else 0
            print(f"Total nodes in Neo4j: {total_nodes}\n")
            
            if total_nodes == 0:
                print("No nodes found. Create some ideas using:")
                print("  poetry run python scripts/test_phase2_retention.py --wait-seconds 60")
                return
            
            # List Idea nodes
            print("=== Idea Nodes ===")
            result = await session.run("MATCH (n:Idea) RETURN n.id as id, n.text as text LIMIT 20")
            ideas = [record async for record in result]
            if ideas:
                for idea in ideas:
                    text_preview = idea["text"][:60] + "..." if len(idea.get("text", "")) > 60 else idea.get("text", "")
                    print(f"  - {idea['id']}: {text_preview}")
            else:
                print("  (no Idea nodes found)")
            
            # List User nodes
            print("\n=== User Nodes ===")
            result = await session.run("MATCH (n:User) RETURN n.id as id, n.user_id as user_id LIMIT 10")
            users = [record async for record in result]
            if users:
                for user in users:
                    print(f"  - {user.get('id', 'N/A')}: user_id={user.get('user_id', 'N/A')}")
            else:
                print("  (no User nodes found)")
            
            # List Preference nodes
            print("\n=== Preference Nodes ===")
            result = await session.run("MATCH (n:Preference) RETURN n.id as id, n.key as key, n.value as value LIMIT 10")
            prefs = [record async for record in result]
            if prefs:
                for pref in prefs:
                    print(f"  - {pref['id']}: {pref.get('key', 'N/A')} = {pref.get('value', 'N/A')}")
            else:
                print("  (no Preference nodes found)")
            
            # List relationships
            print("\n=== Relationships ===")
            result = await session.run("MATCH ()-[r]->() RETURN type(r) as rel_type, count(*) as count LIMIT 10")
            rels = [record async for record in result]
            if rels:
                for rel in rels:
                    print(f"  - {rel['rel_type']}: {rel['count']} occurrences")
            else:
                print("  (no relationships found)")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(check_nodes())

