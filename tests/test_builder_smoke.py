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

"""Phase 1 integration / smoke tests.

Runs ``sphinx-build -b longmd`` on the basic_mixed_source fixture
and validates the output against the contracts and acceptance criteria.
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
def built_output() -> Path:
    """Run sphinx-build once for the whole module and return the outdir."""
    srcdir = FIXTURES_DIR / "basic_mixed_source"
    outdir = BUILD_DIR / "basic_mixed_source"

    if outdir.exists():
        import shutil
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            sys.executable, "-m", "sphinx",
            "-b", "longmd",
            "-W",  # turn warnings into errors (strict Sphinx build)
            str(srcdir),
            str(outdir),
        ],
        capture_output=True,
        text=True,
    )
    # Print output for debugging if it fails.
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    assert result.returncode == 0, f"sphinx-build failed:\n{result.stderr}"
    return outdir


# ==================================================================
# Artifact existence checks
# ==================================================================

class TestArtifactExistence:
    def test_longmd_file_exists(self, built_output: Path) -> None:
        md_path = built_output / "index.longmd.md"
        assert md_path.exists(), f"Missing {md_path}"

    def test_sidecar_file_exists(self, built_output: Path) -> None:
        sidecar_path = built_output / "index.longmd.map.json"
        assert sidecar_path.exists(), f"Missing {sidecar_path}"

    def test_assets_dir_exists(self, built_output: Path) -> None:
        assets_dir = built_output / "assets"
        assert assets_dir.exists(), f"Missing {assets_dir}"

    def test_image_copied(self, built_output: Path) -> None:
        img = built_output / "assets" / "diagram.png"
        assert img.exists(), f"Missing copied image {img}"


# ==================================================================
# Output content checks
# ==================================================================

class TestOutputContent:
    @pytest.fixture()
    def md_text(self, built_output: Path) -> str:
        return (built_output / "index.longmd.md").read_text(encoding="utf-8")

    # --- Document ordering ---

    def test_root_doc_appears_first(self, md_text: str) -> None:
        first_start = md_text.index('longmd:start-file docname="index"')
        assert first_start < md_text.index('longmd:start-file docname="intro"')
        assert first_start < md_text.index('longmd:start-file docname="api"')

    def test_each_doc_appears_once(self, md_text: str) -> None:
        assert md_text.count('longmd:start-file docname="index"') == 1
        assert md_text.count('longmd:start-file docname="intro"') == 1
        assert md_text.count('longmd:start-file docname="api"') == 1

    # --- Boundary markers ---

    def test_start_end_boundary_comments(self, md_text: str) -> None:
        for docname in ("index", "intro", "api"):
            assert f'longmd:start-file docname="{docname}"' in md_text
            assert f'longmd:end-file docname="{docname}"' in md_text

    def test_document_anchors_present(self, md_text: str) -> None:
        assert '<a id="document-index"></a>' in md_text
        assert '<a id="document-intro"></a>' in md_text
        assert '<a id="document-api"></a>' in md_text

    # --- Synthetic TOC ---

    def test_synthetic_toc_present(self, md_text: str) -> None:
        assert "**Contents**" in md_text
        assert "#document-index" in md_text
        assert "#document-intro" in md_text
        assert "#document-api" in md_text

    # --- Headings ---

    def test_root_title_heading(self, md_text: str) -> None:
        # Root title must be exactly H1, not H2.
        assert "\n# TestProject\n" in md_text or md_text.startswith("# TestProject\n")

    def test_child_doc_title_headings(self, md_text: str) -> None:
        # Child doc sections are nested inside the root section in the
        # assembled tree, so their titles are at depth 2 → ##.
        assert "\n## Introduction\n" in md_text
        assert "\n## API Reference\n" in md_text

    # --- Basic prose ---

    def test_emphasis(self, md_text: str) -> None:
        assert "*mixed-source*" in md_text

    def test_strong(self, md_text: str) -> None:
        assert "**TestProject**" in md_text

    def test_inline_code(self, md_text: str) -> None:
        assert "`frob()`" in md_text

    # --- Lists ---

    def test_bullet_list(self, md_text: str) -> None:
        assert "- Feature one" in md_text
        assert "- Feature two" in md_text

    def test_enumerated_list(self, md_text: str) -> None:
        assert "1. Install the package" in md_text or "1. The API is stable" in md_text

    # --- Code blocks ---

    def test_fenced_code_block(self, md_text: str) -> None:
        assert "```python" in md_text
        assert 'print("Hello from longmd!")' in md_text

    # --- Block quote ---

    def test_block_quote(self, md_text: str) -> None:
        assert "> This is a blockquote" in md_text

    # --- Images ---

    def test_image_reference(self, md_text: str) -> None:
        assert "![Architecture diagram]" in md_text
        assert "assets/diagram.png" in md_text

    # --- Cross-references are same-file fragments ---

    def test_internal_links_are_fragments(self, md_text: str) -> None:
        # All internal links should be same-file fragment links (start with #).
        import re
        # Find all markdown links.
        links = re.findall(r'\]\((#[^)]+)\)', md_text)
        assert len(links) > 0, "No internal fragment links found"
        for link in links:
            assert link.startswith("#"), f"Internal link is not a fragment: {link}"


# ==================================================================
# Sidecar checks
# ==================================================================

class TestSidecar:
    @pytest.fixture()
    def sidecar(self, built_output: Path) -> dict:
        path = built_output / "index.longmd.map.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_version(self, sidecar: dict) -> None:
        assert sidecar["version"] == "1.0"

    def test_profile(self, sidecar: dict) -> None:
        assert sidecar["profile"] == "longmd_myst_v0"

    def test_root_doc(self, sidecar: dict) -> None:
        assert sidecar["root_doc"] == "index"

    def test_output_file(self, sidecar: dict) -> None:
        assert sidecar["output_file"] == "index.longmd.md"

    def test_document_order_populated(self, sidecar: dict) -> None:
        order = sidecar["document_order"]
        assert isinstance(order, list)
        assert len(order) >= 3
        assert order[0] == "index"
        assert "intro" in order
        assert "api" in order

    def test_anchors_non_empty(self, sidecar: dict) -> None:
        assert len(sidecar["anchors"]) > 0

    def test_stats_emitted_lines(self, sidecar: dict) -> None:
        assert sidecar["stats"]["emitted_lines"] > 0

    def test_stats_documents_total(self, sidecar: dict) -> None:
        assert sidecar["stats"]["documents_total"] >= 3

    def test_stats_anchors_total(self, sidecar: dict) -> None:
        assert sidecar["stats"]["anchors_total"] > 0

    def test_spans_non_empty(self, sidecar: dict) -> None:
        assert len(sidecar["spans"]) > 0

    def test_spans_have_real_line_numbers(self, sidecar: dict) -> None:
        """Every span must have non-zero 1-based line numbers."""
        for span in sidecar["spans"]:
            assert span["out_start_line"] >= 1, f"Zero start line: {span}"
            assert span["out_end_line"] >= 1, f"Zero end line: {span}"
            assert span["out_end_line"] >= span["out_start_line"], \
                f"End before start: {span}"

    def test_spans_are_monotonic(self, sidecar: dict) -> None:
        """Span start lines should be non-decreasing (monotonic)."""
        starts = [s["out_start_line"] for s in sidecar["spans"]]
        for i in range(1, len(starts)):
            assert starts[i] >= starts[i - 1], \
                f"Non-monotonic spans at index {i}: {starts[i-1]} > {starts[i]}"
