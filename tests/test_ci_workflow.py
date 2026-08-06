"""Tests for GitHub Actions workflow coverage."""

from __future__ import annotations

from pathlib import Path

import yaml


def test_ci_workflow_supports_push_pr_and_manual_dispatch():
    """CI should cover pre-merge checks and allow manual verification on main."""
    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text())

    triggers = workflow.get("on") or workflow[True]

    assert "pull_request" in triggers
    assert "push" in triggers
    assert "workflow_dispatch" in triggers
