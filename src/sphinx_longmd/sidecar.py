"""Sidecar model and JSON serialisation.

The sidecar (``.longmd.map.json``) is the machine-consumable provenance
file emitted alongside the long Markdown artifact.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from sphinx_longmd.context import LossRecord, SpanRecord, WarningRecord


@dataclass
class SidecarModel:
    """Top-level sidecar data model.

    Populated incrementally during the build and serialised at the end.
    """

    version: str = "1.0"
    profile: str = "longmd_myst_v0"
    root_doc: str = ""
    output_file: str = ""
    document_order: list[str] = field(default_factory=list)
    anchors: dict[str, str] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)
    objects: dict[str, Any] = field(default_factory=dict)
    assets: list[dict[str, Any]] = field(default_factory=list)
    spans: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    losses: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Population helpers
    # ------------------------------------------------------------------

    def add_spans(self, records: list[SpanRecord]) -> None:
        for rec in records:
            self.spans.append(asdict(rec))

    def add_warnings(self, records: list[WarningRecord]) -> None:
        for rec in records:
            self.warnings.append(asdict(rec))

    def add_losses(self, records: list[LossRecord]) -> None:
        for rec in records:
            self.losses.append(asdict(rec))

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "profile": self.profile,
            "root_doc": self.root_doc,
            "output_file": self.output_file,
            "document_order": self.document_order,
            "anchors": self.anchors,
            "aliases": self.aliases,
            "objects": self.objects,
            "assets": self.assets,
            "spans": self.spans,
            "warnings": self.warnings,
            "losses": self.losses,
            "stats": self.stats,
        }

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, ensure_ascii=False)
            fh.write("\n")
