"""Phase 3 integration tests.

Tests custom/third-party node survival, raw content policy,
strict vs non-strict modes, and diagnostics.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
BUILD_DIR = Path(__file__).parent / "_build"


def _run_build(
    srcdir: Path,
    outdir: Path,
    *,
    confdir: Path | None = None,
    expect_fail: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run sphinx-build and return the result."""
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "sphinx",
        "-b", "longmd",
        str(srcdir),
        str(outdir),
    ]
    if confdir is not None:
        cmd.extend(["-c", str(confdir)])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if not expect_fail and result.returncode != 0:
        print("STDOUT:", result.stdout[-2000:])
        print("STDERR:", result.stderr[-2000:])
    return result


# ==================================================================
# Non-strict mode (default)
# ==================================================================

class TestNonStrictCustomNodes:
    """Custom nodes degrade gracefully in non-strict mode."""

    @pytest.fixture(scope="class")
    def built(self) -> Path:
        srcdir = FIXTURES_DIR / "custom_nodes"
        outdir = BUILD_DIR / "custom_nodes_nonstrict"
        result = _run_build(srcdir, outdir)
        assert result.returncode == 0, f"Build failed:\n{result.stderr[-1000:]}"
        return outdir

    @pytest.fixture()
    def md(self, built: Path) -> str:
        return (built / "index.longmd.md").read_text()

    @pytest.fixture()
    def sidecar(self, built: Path) -> dict:
        return json.loads((built / "index.longmd.map.json").read_text())

    def test_build_succeeds(self, built: Path) -> None:
        assert (built / "index.longmd.md").exists()

    def test_custom_node_does_not_crash(self, md: str) -> None:
        # The build completed — custom_card did not crash.
        assert "Phase3Test" in md

    def test_custom_node_fallback_block(self, md: str) -> None:
        # The custom card node should be emitted as a sphinx-node block
        # OR its text content passed through.
        assert "custom card element" in md

    def test_raw_html_passes_through(self, md: str) -> None:
        assert "custom-banner" in md

    def test_raw_latex_omitted_from_body(self, md: str) -> None:
        assert "\\newpage" not in md

    def test_warnings_recorded(self, sidecar: dict) -> None:
        warnings = sidecar.get("warnings", [])
        # Should have at least one warning for the custom node or raw latex.
        codes = [w["code"] for w in warnings]
        assert any(c in ("unknown_node", "raw_content_omitted", "unresolved_xref")
                   for c in codes), f"Expected a warning, got codes: {codes}"

    def test_losses_recorded(self, sidecar: dict) -> None:
        losses = sidecar.get("losses", [])
        codes = [l["code"] for l in losses]
        assert any(c in ("custom_node_degraded", "raw_content_sidecar_only")
                   for c in codes), f"Expected a loss, got codes: {codes}"

    def test_stats_has_fallback_count(self, sidecar: dict) -> None:
        stats = sidecar.get("stats", {})
        # fallback_nodes_total should exist.
        assert "fallback_nodes_total" in stats

    def test_diagnostics_timing(self, sidecar: dict) -> None:
        stats = sidecar.get("stats", {})
        timing = stats.get("timing_ms", {})
        assert "assemble" in timing
        assert "emit" in timing
        assert "plan" in timing


# ==================================================================
# Strict mode
# ==================================================================

class TestStrictMode:
    """Strict mode must fail deterministically on unsupported nodes."""

    def test_strict_fails_on_custom_node(self) -> None:
        srcdir = FIXTURES_DIR / "custom_nodes"
        outdir = BUILD_DIR / "custom_nodes_strict"

        # Use the strict conf.
        confdir = srcdir  # We'll override via -D
        result = _run_build(
            srcdir, outdir,
            expect_fail=True,
        )
        # The default conf is non-strict, so this should pass.
        # We need to use the strict conf.
        if outdir.exists():
            shutil.rmtree(outdir)
        outdir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable, "-m", "sphinx",
            "-b", "longmd",
            "-D", "longmd_strict=1",
            str(srcdir),
            str(outdir),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        # Should fail because of the custom_card node.
        assert result.returncode != 0, \
            "Strict mode should have failed on custom_card node"
        assert "strict" in result.stdout.lower() or "strict" in result.stderr.lower() \
            or "StrictModeError" in result.stdout or "RuntimeError" in result.stdout, \
            f"Expected strict-mode error message, got:\n{result.stdout[-500:]}"

    def test_nonstrict_same_fixture_succeeds(self) -> None:
        srcdir = FIXTURES_DIR / "custom_nodes"
        outdir = BUILD_DIR / "custom_nodes_nonstrict_check"
        result = _run_build(srcdir, outdir)
        assert result.returncode == 0


# ==================================================================
# Raw content policy
# ==================================================================

class TestRawContentPolicy:
    @pytest.fixture(scope="class")
    def built(self) -> Path:
        srcdir = FIXTURES_DIR / "custom_nodes"
        outdir = BUILD_DIR / "custom_nodes_raw"
        result = _run_build(srcdir, outdir)
        assert result.returncode == 0
        return outdir

    @pytest.fixture()
    def md(self, built: Path) -> str:
        return (built / "index.longmd.md").read_text()

    @pytest.fixture()
    def sidecar(self, built: Path) -> dict:
        return json.loads((built / "index.longmd.map.json").read_text())

    def test_html_raw_in_body(self, md: str) -> None:
        assert "custom-banner" in md

    def test_latex_raw_not_in_body(self, md: str) -> None:
        assert "\\newpage" not in md

    def test_latex_raw_warning_in_sidecar(self, sidecar: dict) -> None:
        warnings = sidecar.get("warnings", [])
        raw_warnings = [w for w in warnings if "raw" in w.get("code", "").lower()]
        assert len(raw_warnings) >= 1, \
            f"Expected raw content warning, got: {[w['code'] for w in warnings]}"


# ==================================================================
# Duplicate anchor handling
# ==================================================================

class TestDuplicateAnchors:
    @pytest.fixture(scope="class")
    def built(self) -> Path:
        srcdir = FIXTURES_DIR / "custom_nodes"
        outdir = BUILD_DIR / "custom_nodes_anchors"
        result = _run_build(srcdir, outdir)
        assert result.returncode == 0
        return outdir

    @pytest.fixture()
    def sidecar(self, built: Path) -> dict:
        return json.loads((built / "index.longmd.map.json").read_text())

    def test_no_duplicate_emitted_ids(self, sidecar: dict) -> None:
        anchors = sidecar.get("anchors", {})
        emitted_ids = list(anchors.values())
        assert len(emitted_ids) == len(set(emitted_ids)), \
            f"Duplicate emitted IDs: {emitted_ids}"


# ==================================================================
# Sidecar completeness
# ==================================================================

class TestSidecarCompleteness:
    @pytest.fixture(scope="class")
    def sidecar(self) -> dict:
        srcdir = FIXTURES_DIR / "custom_nodes"
        outdir = BUILD_DIR / "custom_nodes_sidecar"
        result = _run_build(srcdir, outdir)
        assert result.returncode == 0
        return json.loads((outdir / "index.longmd.map.json").read_text())

    def test_required_keys(self, sidecar: dict) -> None:
        for key in ("version", "profile", "root_doc", "output_file",
                     "document_order", "anchors", "spans", "warnings", "stats"):
            assert key in sidecar, f"Missing required sidecar key: {key}"

    def test_losses_key(self, sidecar: dict) -> None:
        assert "losses" in sidecar

    def test_stats_complete(self, sidecar: dict) -> None:
        stats = sidecar["stats"]
        for key in ("documents_total", "anchors_total", "emitted_lines",
                     "warnings_total", "losses_total", "fallback_nodes_total",
                     "objects_total"):
            assert key in stats, f"Missing stat: {key}"

    def test_timing_buckets(self, sidecar: dict) -> None:
        timing = sidecar["stats"].get("timing_ms", {})
        for bucket in ("assemble", "plan", "emit", "copy_assets"):
            assert bucket in timing, f"Missing timing bucket: {bucket}"
