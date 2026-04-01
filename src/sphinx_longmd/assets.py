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

"""Asset registration and copy/rewrite.

This module collects referenced images and downloads during emission,
copies them into the output ``assets/`` directory, and provides the
rewritten relative path for use in the Markdown body.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from sphinx_longmd.context import WarningRecord

if TYPE_CHECKING:
    from docutils import nodes

    from sphinx_longmd.context import EmissionContext


@dataclass(slots=True)
class AssetRecord:
    kind: str  # "image" | "download"
    source_uri: str
    source_docname: str | None = None
    output_path: str = ""
    original_path: str | None = None


class AssetManager:
    """Tracks assets referenced by the emitted Markdown and copies them."""

    def __init__(self) -> None:
        self._records: list[AssetRecord] = []
        self._seen_uris: dict[str, str] = {}  # source_uri -> output_path

    def register_image(
        self, uri: str, *, docname: str | None = None
    ) -> str:
        """Register an image and return the output-relative path."""
        if uri in self._seen_uris:
            return self._seen_uris[uri]

        basename = Path(uri).name
        output_rel = f"assets/{basename}"

        # Handle filename collisions deterministically.
        if output_rel in {r.output_path for r in self._records}:
            stem = Path(basename).stem
            suffix = Path(basename).suffix
            for i in range(1, 10_000):
                candidate = f"assets/{stem}-{i}{suffix}"
                if candidate not in {r.output_path for r in self._records}:
                    output_rel = candidate
                    break

        rec = AssetRecord(
            kind="image",
            source_uri=uri,
            source_docname=docname,
            output_path=output_rel,
            original_path=uri,
        )
        self._records.append(rec)
        self._seen_uris[uri] = output_rel
        return output_rel

    def register_from_node(
        self, node: nodes.Node, ctx: EmissionContext
    ) -> str | None:
        """Extract an image URI from a node and register it."""
        uri: str = node.get("uri", "")  # type: ignore[union-attr]
        if not uri:
            return None
        return self.register_image(uri, docname=ctx.current_docname)

    def finalize(self, srcdir: Path, outdir: Path) -> tuple[list[AssetRecord], list[WarningRecord]]:
        """Copy all registered assets into *outdir* and return records."""
        warnings: list[WarningRecord] = []
        assets_dir = outdir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        for rec in self._records:
            src = srcdir / rec.source_uri
            dst = outdir / rec.output_path
            if not src.exists():
                # Also try inside an _images or images subdir as Sphinx may
                # have already copied it.
                warnings.append(
                    WarningRecord(
                        code="asset_missing",
                        message=f"Asset not found: {src}",
                        severity="error",
                        source_docname=rec.source_docname,
                    )
                )
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        return self._records, warnings

    def all_records(self) -> list[AssetRecord]:
        return list(self._records)
