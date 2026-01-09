#!/usr/bin/env python3
"""Retention test for Phase 2 data.

This script:
  - Creates a couple of ideas in the knowledge graph
  - Shows their IDs and current idea count
  - Waits for a specified time (default: 60 seconds)
  - Deletes the created ideas
  - Shows the idea count after cleanup

Use this to manually observe persistence in `data/henry_graph.db`
between creation and deletion.

Run with (default 60s wait):
    poetry run python scripts/test_phase2_retention.py

Or with a custom wait time in seconds:
    poetry run python scripts/test_phase2_retention.py --wait-seconds 10
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.knowledge_service import KnowledgeService  # noqa: E402


def print_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2 retention test (ideas).")
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=60,
        help="Seconds to wait before deleting the created ideas (default: 60).",
    )
    args = parser.parse_args()

    wait_seconds = max(1, args.wait_seconds)

    print_header("H.E.N.R.Y. Phase 2 Retention Test (Ideas)")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Wait time: {wait_seconds} seconds\n")

    knowledge = KnowledgeService.get_instance()

    # Baseline
    existing = knowledge.list_ideas()
    print(f"Existing ideas before test: {len(existing)}")

    # Create a couple of ideas
    print_header("Creating test ideas")
    idea1 = knowledge.create_idea(
        text="Retention test idea 1 - safe to delete",
        tags=["retention_test", "temp"],
    )
    idea2 = knowledge.create_idea(
        text="Retention test idea 2 - safe to delete",
        tags=["retention_test", "temp"],
    )

    print(f"Created idea 1 ID: {idea1.id}")
    print(f"Created idea 2 ID: {idea2.id}")

    ideas_after_create = knowledge.list_ideas()
    print(f"\nIdeas after creation: {len(ideas_after_create)}")
    print("You can now inspect the database (e.g., data/henry_graph.db) if desired.")

    # Wait
    print_header("Waiting before cleanup")
    for remaining in range(wait_seconds, 0, -1):
        print(f"\rDeleting in {remaining:3d} seconds...", end="", flush=True)
        time.sleep(1)
    print("\rProceeding with cleanup...         ")

    # Delete the test ideas
    print_header("Deleting test ideas")
    deleted1 = knowledge.delete_idea(idea1.id)
    deleted2 = knowledge.delete_idea(idea2.id)
    print(f"Deleted idea 1 ({idea1.id}): {deleted1}")
    print(f"Deleted idea 2 ({idea2.id}): {deleted2}")

    final_ideas = knowledge.list_ideas()
    print(f"\nIdeas after cleanup: {len(final_ideas)}")

    print_header("Retention test complete")
    print("Created ideas were left in the database during the wait interval,")
    print("and have now been cleaned up. You can rerun this script as needed.")


if __name__ == "__main__":
    main()


