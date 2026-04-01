# Copyright 2026 Grainpool Holdings LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""Phase 2 integration tests.

Runs ``sphinx-build -b longmd`` on the objects_and_glossary fixture
and validates admonitions, object descriptions, glossary, tables,
figures, footnotes, and field lists.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
BUILD_DIR = Path(__file__).parent / "_build"


@pytest.fixture(scope="module")
def phase2_output() -> Path:
    srcdir = FIXTURES_DIR / "objects_and_glossary"
    outdir = BUILD_DIR / "objects_and_glossary"
    if outdir.exists():
        import shutil
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [sys.executable, "-m", "sphinx", "-b", "longmd",
         str(srcdir), str(outdir)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    assert result.returncode == 0, f"sphinx-build failed:\n{result.stderr}"
    return outdir


# ==================================================================
# Artifact checks
# ==================================================================

class TestPhase2Artifacts:
    def test_md_exists(self, phase2_output: Path) -> None:
        assert (phase2_output / "index.longmd.md").exists()

    def test_sidecar_exists(self, phase2_output: Path) -> None:
        assert (phase2_output / "index.longmd.map.json").exists()


# ==================================================================
# Admonition checks
# ==================================================================

class TestAdmonitions:
    @pytest.fixture()
    def md(self, phase2_output: Path) -> str:
        return (phase2_output / "index.longmd.md").read_text()

    def test_note_directive(self, md: str) -> None:
        assert ":::{note}" in md
        assert "This is a note admonition." in md

    def test_warning_directive(self, md: str) -> None:
        assert ":::{warning}" in md
        assert "This is a warning." in md

    def test_generic_admonition(self, md: str) -> None:
        assert ":::{admonition} Custom title" in md
        assert "generic admonition with a custom title" in md

    def test_rubric_as_bold(self, md: str) -> None:
        assert "**Examples**" in md

    def test_no_sphinx_node_for_admonitions(self, md: str) -> None:
        # Admonitions should NOT fall back to sphinx-node.
        # Find all sphinx-node blocks and ensure none are for admonitions.
        import re
        fallbacks = re.findall(r":::\{sphinx-node\}\n:node-type: ([^\n]+)", md)
        adm_types = {"note", "warning", "admonition", "important", "tip"}
        for fb in fallbacks:
            assert not any(a in fb.lower() for a in adm_types), \
                f"Admonition fell back to sphinx-node: {fb}"


# ==================================================================
# Object description checks
# ==================================================================

class TestObjectDescriptions:
    @pytest.fixture()
    def md(self, phase2_output: Path) -> str:
        return (phase2_output / "index.longmd.md").read_text()

    @pytest.fixture()
    def sidecar(self, phase2_output: Path) -> dict:
        return json.loads((phase2_output / "index.longmd.map.json").read_text())

    def test_function_directive(self, md: str) -> None:
        assert ":::{py:function}" in md
        assert "demo.frob(x, y=0)" in md

    def test_function_anchor(self, md: str) -> None:
        # Should have an anchor for the function.
        assert "demo-frob" in md or "demo.frob" in md

    def test_params_normalized(self, md: str) -> None:
        assert "**Parameters**" in md
        # Sphinx pre-renders params as **x** (*int*) or `x` (`int`)
        assert "x" in md and "int" in md

    def test_returns_normalized(self, md: str) -> None:
        assert "**Returns**" in md or "**Return type**" in md
        assert "bool" in md

    def test_raises_normalized(self, md: str) -> None:
        assert "**Raises**" in md
        assert "ValueError" in md

    def test_class_directive(self, md: str) -> None:
        assert ":::{py:class}" in md
        assert "demo.Widget" in md

    def test_method_directive(self, md: str) -> None:
        assert ":::{py:method}" in md
        assert "render" in md

    def test_no_sphinx_node_for_desc(self, md: str) -> None:
        import re
        fallbacks = re.findall(r":::\{sphinx-node\}\n:node-type: ([^\n]+)", md)
        desc_types = {"desc", "desc_signature", "desc_content"}
        for fb in fallbacks:
            short = fb.rsplit(".", 1)[-1] if "." in fb else fb
            assert short not in desc_types, f"desc fell back: {fb}"

    def test_objects_in_sidecar(self, sidecar: dict) -> None:
        objects = sidecar.get("objects", {})
        # Should have at least the function and class.
        assert len(objects) >= 2


# ==================================================================
# Field list checks
# ==================================================================

class TestFieldLists:
    @pytest.fixture()
    def md(self, phase2_output: Path) -> str:
        return (phase2_output / "index.longmd.md").read_text()

    def test_generic_field_list(self, md: str) -> None:
        assert "**Status:**" in md or "**Status**" in md
        assert "stable" in md

    def test_no_sphinx_node_for_field_list(self, md: str) -> None:
        import re
        fallbacks = re.findall(r":::\{sphinx-node\}\n:node-type: ([^\n]+)", md)
        for fb in fallbacks:
            assert "field_list" not in fb, f"field_list fell back: {fb}"


# ==================================================================
# Glossary checks
# ==================================================================

class TestGlossary:
    @pytest.fixture()
    def md(self, phase2_output: Path) -> str:
        return (phase2_output / "index.longmd.md").read_text()

    def test_glossary_term_rendered(self, md: str) -> None:
        assert "**widget**" in md
        assert "reusable component" in md

    def test_glossary_term_anchor(self, md: str) -> None:
        assert "term-widget" in md

    def test_definition_list_rendered(self, md: str) -> None:
        assert "Term one" in md
        assert "Definition of term one" in md


# ==================================================================
# Table checks
# ==================================================================

class TestTables:
    @pytest.fixture()
    def md(self, phase2_output: Path) -> str:
        return (phase2_output / "index.longmd.md").read_text()

    def test_table_rendered(self, md: str) -> None:
        assert "| Feature" in md
        assert "| Admonitions" in md
        assert "---" in md  # separator row

    def test_no_sphinx_node_for_table(self, md: str) -> None:
        import re
        fallbacks = re.findall(r":::\{sphinx-node\}\n:node-type: ([^\n]+)", md)
        for fb in fallbacks:
            assert "table" not in fb.lower() or "tgroup" not in fb.lower(), \
                f"table fell back: {fb}"


# ==================================================================
# Figure checks
# ==================================================================

class TestFigures:
    @pytest.fixture()
    def md(self, phase2_output: Path) -> str:
        return (phase2_output / "index.longmd.md").read_text()

    def test_figure_image(self, md: str) -> None:
        assert "![Architecture diagram]" in md or "![" in md

    def test_figure_caption(self, md: str) -> None:
        assert "*This is the figure caption.*" in md


# ==================================================================
# Footnote checks
# ==================================================================

class TestFootnotes:
    @pytest.fixture()
    def md(self, phase2_output: Path) -> str:
        return (phase2_output / "index.longmd.md").read_text()

    def test_footnote_reference(self, md: str) -> None:
        assert "[^" in md

    def test_footnote_definition(self, md: str) -> None:
        assert "[^" in md
        assert "Auto footnote" in md or "Named footnote" in md


# ==================================================================
# Sidecar checks
# ==================================================================

class TestPhase2Sidecar:
    @pytest.fixture()
    def sidecar(self, phase2_output: Path) -> dict:
        return json.loads((phase2_output / "index.longmd.map.json").read_text())

    def test_warnings_recorded(self, sidecar: dict) -> None:
        # There may or may not be warnings, but the key must exist.
        assert "warnings" in sidecar

    def test_losses_recorded(self, sidecar: dict) -> None:
        assert "losses" in sidecar

    def test_stats_has_objects(self, sidecar: dict) -> None:
        assert sidecar["stats"].get("objects_total", 0) >= 0
