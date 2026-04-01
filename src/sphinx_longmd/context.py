"""Dataclasses for emission context, spans, warnings, and emissions.

This module defines the core data structures that flow through the entire
emission pipeline. Every block emitter returns an ``Emission``; the central
writer accumulates line numbers and provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from docutils import nodes

    from sphinx_longmd.anchors import AnchorRegistry
    from sphinx_longmd.builder import LongMdBuilder
    from sphinx_longmd.sidecar import SidecarModel

    from sphinx.environment import BuildEnvironment


@dataclass(frozen=True, slots=True)
class SourceLoc:
    """Source location of a doctree node."""

    docname: str | None = None
    source_path: str | None = None
    line: int | None = None


@dataclass(slots=True)
class SpanRecord:
    """Maps an emitted line range back to the source node that produced it."""

    out_start_line: int
    out_end_line: int
    source_docname: str | None = None
    source_path: str | None = None
    source_line: int | None = None
    node_type: str = ""
    anchors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WarningRecord:
    """A warning/info/error generated during emission."""

    code: str
    message: str
    severity: Literal["info", "warning", "error"] = "warning"
    source_docname: str | None = None
    source_path: str | None = None
    source_line: int | None = None
    node_type: str | None = None


@dataclass(slots=True)
class LossRecord:
    """Records semantic content that was degraded or lost during emission."""

    code: str
    level: Literal["minor", "moderate", "major"] = "moderate"
    node_type: str = ""
    source_docname: str | None = None
    source_path: str | None = None
    source_line: int | None = None
    details: str = ""


@dataclass
class Emission:
    """Result returned by every block/inline emitter.

    Carries the emitted text plus any provenance records generated.
    """

    text: str = ""
    spans: list[SpanRecord] = field(default_factory=list)
    warnings: list[WarningRecord] = field(default_factory=list)
    losses: list[LossRecord] = field(default_factory=list)


@dataclass
class EmissionContext:
    """Mutable context threaded through the emission pipeline.

    Provides access to the builder, environment, registries, and the
    current output-line cursor.
    """

    builder: LongMdBuilder
    env: BuildEnvironment
    root_doc: str
    assembled_doctree: nodes.document
    anchor_registry: AnchorRegistry
    sidecar: SidecarModel
    current_docname: str = ""
    current_source_path: str | None = None
    output_line_cursor: int = 1

    # Tracks toctree nesting level: 0 for root doc, 1 for child docs, etc.
    doc_depth: int = 0

    # Phase 3: strict mode and raw-content policy.
    strict: bool = False
    raw_html: bool = True

    # Accumulate warnings and losses across the whole build.
    warnings: list[WarningRecord] = field(default_factory=list)
    losses: list[LossRecord] = field(default_factory=list)
    spans: list[SpanRecord] = field(default_factory=list)
