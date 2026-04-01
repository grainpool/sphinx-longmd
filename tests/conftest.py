"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
BUILD_DIR = Path(__file__).parent / "_build"


@pytest.fixture()
def basic_mixed_source_dir() -> Path:
    return FIXTURES_DIR / "basic_mixed_source"


@pytest.fixture()
def basic_mixed_build_dir() -> Path:
    d = BUILD_DIR / "basic_mixed_source"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)
    return d
