"""Tests for the build configuration."""

import tomllib
from pathlib import Path


PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def load_pyproject() -> dict:
    """Read the project's build configuration."""
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_packages_are_pinned_to_backend() -> None:
    """Auto-discovery breaks when a second top-level directory exists.

    The daily workflow commits data/seen_items.json, so relying on
    setuptools flat-layout discovery meant the first successful run
    created a data/ directory and broke the build for every run
    after it.
    """
    config = load_pyproject()

    include = (
        config["tool"]["setuptools"]["packages"]["find"]["include"]
    )

    assert include == ["backend*"]


def test_declared_dependencies_are_imported() -> None:
    """A dependency nothing imports is install time for nothing."""
    config = load_pyproject()

    declared = {
        requirement.split(">=")[0].split("[")[0].strip()
        for requirement in config["project"]["dependencies"]
    }

    assert declared == {
        "feedparser",
        "firebase-admin",
        "httpx",
        "pydantic",
        "pydantic-settings",
    }
