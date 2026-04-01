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

"""LongMdBuilder — Sphinx builder entry point and orchestration.

Owns the write phase only. Delegates assembly to :mod:`assemble`,
anchor planning to :mod:`anchors`, emission to :mod:`emit.writer`,
asset handling to :mod:`assets`, and sidecar serialisation to
:mod:`sidecar`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from docutils import nodes
from sphinx import addnodes
from sphinx.builders import Builder
from sphinx.util import logging as sphinx_logging

from sphinx_longmd.anchors import AnchorRegistry, slugify_docname
from sphinx_longmd.assets import AssetManager
from sphinx_longmd.assemble import (
    assemble_master_doctree,
    compute_document_order,
    iter_doc_boundaries,
)
from sphinx_longmd.context import EmissionContext, WarningRecord
from sphinx_longmd.diagnostics import Diagnostics
from sphinx_longmd.emit.fallback import StrictModeError, register_fallback_emitters
from sphinx_longmd.emit.inline import register_inline_emitters
from sphinx_longmd.emit.objects import register_object_emitters
from sphinx_longmd.emit.sphinx_blocks import register_sphinx_block_emitters
from sphinx_longmd.emit.structural import register_structural_emitters
from sphinx_longmd.emit.writer import EmitterRegistry, write_master_document
from sphinx_longmd.sidecar import SidecarModel

logger = sphinx_logging.getLogger(__name__)


class LongMdBuilder(Builder):
    """Sphinx builder that emits one long-form Markdown artifact."""

    name = "longmd"
    format = "longmd"
    epilog = "The long Markdown file is in %(outdir)s."

    allow_parallel = False

    supported_image_types = [
        "image/svg+xml",
        "image/png",
        "image/gif",
        "image/jpeg",
    ]

    # ------------------------------------------------------------------
    # Builder protocol
    # ------------------------------------------------------------------

    def get_outdated_docs(self) -> str:
        return "all documents"

    def get_target_uri(self, docname: str, typ: str | None = None) -> str:
        return "#document-" + slugify_docname(docname)

    def get_relative_uri(
        self, from_: str, to: str, typ: str | None = None
    ) -> str:
        return self.get_target_uri(to, typ)

    def prepare_writing(self, docnames: set[str]) -> None:
        pass

    def write_doc(self, docname: str, doctree: nodes.document) -> None:
        # Not used — we override write_documents() for single-file output.
        pass

    def write(
        self,
        build_docnames: set[str] | None,
        updated_docnames: set[str],
        method: str = "update",
    ) -> None:
        """Override the top-level write to call write_documents directly."""
        if build_docnames is None or build_docnames == "all":  # type: ignore[comparison-overlap]
            build_docnames = set(self.env.found_docs)
        self.write_documents(build_docnames)

    def write_documents(self, docnames: set[str]) -> None:
        """Assemble, plan, emit, copy assets, write sidecar."""
        diag = Diagnostics()
        root_doc: str = self.env.config.root_doc

        # -- A. Assemble --------------------------------------------------
        with diag.timer("assemble"):
            assembled = assemble_master_doctree(self)

        # -- B. Document order & boundaries --------------------------------
        with diag.timer("plan"):
            boundaries = iter_doc_boundaries(assembled)
            doc_order = compute_document_order(assembled, root_doc)

            # Build anchor registry.
            anchor_reg = AnchorRegistry()
            self._plan_anchors(assembled, anchor_reg, doc_order, boundaries)

        diag.inc("documents_total", len(doc_order))

        # -- C. Build emission context -------------------------------------
        asset_mgr = AssetManager()
        self._asset_manager = asset_mgr  # Expose so image emitter can reach it.

        sidecar = SidecarModel(
            root_doc=root_doc,
            output_file=f"{root_doc}.longmd.md",
            document_order=doc_order,
        )

        ctx = EmissionContext(
            builder=self,
            env=self.env,
            root_doc=root_doc,
            assembled_doctree=assembled,
            anchor_registry=anchor_reg,
            sidecar=sidecar,
            current_docname=root_doc,
            strict=bool(self.env.config.longmd_strict),
            raw_html=bool(self.env.config.longmd_raw_html),
        )

        # -- D. Build emitter registry ------------------------------------
        registry = EmitterRegistry()
        register_structural_emitters(registry)
        register_inline_emitters(registry)
        register_sphinx_block_emitters(registry)
        register_object_emitters(registry)
        register_fallback_emitters(registry)

        # -- E. Emit -------------------------------------------------------
        with diag.timer("emit"):
            # Synthesise top-level TOC.
            toc_md = self._synthetic_toc(doc_order, anchor_reg)

            # Emit root document boundary header.
            root_source = ""
            for b in boundaries:
                if b.docname == root_doc:
                    root_source = b.source_path or ""
                    break
            root_slug = slugify_docname(root_doc)
            root_header = (
                f'<a id="document-{root_slug}"></a>\n'
                f'<!-- longmd:start-file docname="{root_doc}" source="{root_source}" -->\n\n'
            )

            # Set the output line cursor to account for the header + TOC
            # that precede the body in the final output.  Lines are 1-based.
            preamble_lines = root_header.count("\n") + toc_md.count("\n")
            ctx.output_line_cursor = 1 + preamble_lines

            try:
                body = write_master_document(assembled, ctx, registry)
            except StrictModeError as exc:
                raise RuntimeError(
                    f"longmd strict-mode build failure: {exc}\n"
                    f"  code={exc.code} node_type={exc.node_type} "
                    f"doc={exc.docname} line={exc.line}"
                ) from exc

            root_footer = f'\n<!-- longmd:end-file docname="{root_doc}" -->\n'

            full_md = root_header + toc_md + body + root_footer

        # -- E2. Strict post-emission checks --------------------------------
        if ctx.strict:
            unresolved = [w for w in ctx.warnings if w.code == "unresolved_xref"]
            if unresolved:
                msgs = "; ".join(w.message for w in unresolved[:5])
                raise RuntimeError(
                    f"longmd strict-mode: {len(unresolved)} unresolved "
                    f"reference(s): {msgs}"
                )

        # -- F. Finalise artefacts -----------------------------------------
        outdir = Path(self.outdir)
        outdir.mkdir(parents=True, exist_ok=True)

        with diag.timer("copy_assets"):
            srcdir = Path(self.env.srcdir)
            asset_records, asset_warnings = asset_mgr.finalize(srcdir, outdir)
            ctx.warnings.extend(asset_warnings)
            diag.inc("assets_total", len(asset_records))

        # Populate sidecar.
        sidecar.anchors = anchor_reg.anchors_dict()
        sidecar.aliases = anchor_reg.aliases_dict()
        sidecar.add_spans(ctx.spans)
        sidecar.add_warnings(ctx.warnings)
        sidecar.add_losses(ctx.losses)
        sidecar.assets = [
            {
                "kind": r.kind,
                "source_uri": r.source_uri,
                "source_docname": r.source_docname,
                "output_path": r.output_path,
            }
            for r in asset_records
        ]

        # Phase 2: populate objects from Sphinx domain data.
        sidecar.objects = self._collect_objects(anchor_reg)

        # Stats.
        diag.inc("emitted_lines", full_md.count("\n"))
        diag.inc("anchors_total", len(anchor_reg.all_records()))
        diag.inc("warnings_total", len(ctx.warnings))
        diag.inc("losses_total", len(ctx.losses))
        diag.inc("objects_total", len(sidecar.objects))
        diag.inc("fallback_nodes_total", sum(
            1 for w in ctx.warnings if w.code == "unknown_node"))
        sidecar.stats = diag.to_stats_dict()

        # Write files.
        md_path = outdir / f"{root_doc}.longmd.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(full_md, encoding="utf-8")

        sidecar_path = outdir / f"{root_doc}.longmd.map.json"
        sidecar.write(sidecar_path)

        logger.info(
            "longmd: wrote %s (%d lines, %d docs, %d anchors)",
            md_path.name,
            full_md.count("\n"),
            len(doc_order),
            len(anchor_reg.all_records()),
        )

    def finish(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _plan_anchors(
        self,
        tree: nodes.document,
        reg: AnchorRegistry,
        doc_order: list[str],
        boundaries: list[Any],
    ) -> None:
        """Pre-scan the assembled tree and register all anchors."""
        # 1. Document-boundary anchors.
        for b in boundaries:
            slug = slugify_docname(b.docname)
            reg.register(
                canonical_key=f"doc::{b.docname}",
                preferred_id=f"document-{slug}",
                docname=b.docname,
                source_path=b.source_path,
                node_type="document_boundary",
            )

        # 2. Section anchors.
        for section in tree.findall(nodes.section):
            ids: list[str] = section.get("ids", [])
            if not ids:
                continue
            docname = self._owning_docname(section)
            primary_id = ids[0]
            alias_ids = ids[1:]
            canonical_key = f"{docname}::{primary_id}"
            if reg.emitted_id_for_canonical(canonical_key) is not None:
                continue  # Already registered (e.g. by a target merge).
            try:
                reg.register(
                    canonical_key=canonical_key,
                    preferred_id=primary_id,
                    aliases=alias_ids,
                    docname=docname,
                    node_type="section",
                )
            except ValueError:
                # Canonical key race (shouldn't happen with guard above).
                logger.debug("Skipping already-registered anchor %s", canonical_key)

        # 3. Explicit target nodes.
        for target in tree.findall(nodes.target):
            ids = target.get("ids", [])
            if not ids:
                continue
            docname = self._owning_docname(target)
            primary_id = ids[0]
            alias_ids = ids[1:]
            canonical_key = f"{docname}::{primary_id}"
            if reg.emitted_id_for_canonical(canonical_key) is not None:
                continue
            try:
                reg.register(
                    canonical_key=canonical_key,
                    preferred_id=primary_id,
                    aliases=alias_ids,
                    docname=docname,
                    node_type="target",
                )
            except ValueError:
                pass  # Guard above should prevent this.

        # 4. Object description anchors (desc_signature nodes).
        for sig in tree.findall(addnodes.desc_signature):
            ids = sig.get("ids", [])
            if not ids:
                continue
            docname = self._owning_docname(sig)
            primary_id = ids[0]
            alias_ids = ids[1:]
            canonical_key = f"{docname}::{primary_id}"
            if reg.emitted_id_for_canonical(canonical_key) is not None:
                continue
            try:
                reg.register(
                    canonical_key=canonical_key,
                    preferred_id=primary_id,
                    aliases=alias_ids,
                    docname=docname,
                    node_type="object_description",
                )
            except ValueError:
                pass  # Already registered via section/target pass.

        # 5. Glossary term anchors.
        for term in tree.findall(nodes.term):
            ids = term.get("ids", [])
            if not ids:
                continue
            docname = self._owning_docname(term)
            for tid in ids:
                canonical_key = f"term::{tid}"
                if reg.emitted_id_for_canonical(canonical_key) is not None:
                    continue
                try:
                    reg.register(
                        canonical_key=canonical_key,
                        preferred_id=tid,
                        docname=docname,
                        node_type="glossary_term",
                    )
                except ValueError:
                    pass

        # 6. Figure anchors.
        for fig in tree.findall(nodes.figure):
            ids = fig.get("ids", [])
            if not ids:
                continue
            docname = self._owning_docname(fig)
            primary_id = ids[0]
            canonical_key = f"{docname}::{primary_id}"
            if reg.emitted_id_for_canonical(canonical_key) is not None:
                continue
            try:
                reg.register(
                    canonical_key=canonical_key,
                    preferred_id=primary_id,
                    docname=docname,
                    node_type="figure",
                )
            except ValueError:
                pass

    def _owning_docname(self, node: nodes.Node) -> str:
        """Walk up the tree to find the nearest ``start_of_file`` docname."""
        current = node.parent
        while current is not None:
            if isinstance(current, addnodes.start_of_file):
                return current.get("docname", "")  # type: ignore[return-value]
            current = current.parent
        return self.env.config.root_doc

    def _synthetic_toc(
        self,
        doc_order: list[str],
        anchor_reg: AnchorRegistry,
    ) -> str:
        """Generate a synthetic table of contents linking to each document."""
        lines = ["**Contents**\n\n"]
        for docname in doc_order:
            slug = slugify_docname(docname)
            # Use the last path segment as a display name.
            display = docname.rsplit("/", 1)[-1].replace("_", " ").replace("-", " ").title()
            lines.append(f"- [{display}](#document-{slug})\n")
        lines.append("\n")
        return "".join(lines)

    def _collect_objects(self, anchor_reg: AnchorRegistry) -> dict[str, Any]:
        """Extract domain object metadata for the sidecar."""
        objects: dict[str, Any] = {}
        try:
            for domain_name, domain in self.env.domains.items():
                for (name, dispname, typ, docname, anchor, prio) in domain.get_objects():
                    key = f"{domain_name}:{typ}:{name}"
                    emitted_id = anchor_reg.lookup_from_existing_id(docname, anchor) or anchor
                    objects[key] = {
                        "domain": str(domain_name),
                        "objtype": str(typ),
                        "qualified_name": str(name),
                        "display_name": str(dispname),
                        "anchor_id": str(emitted_id),
                        "source_docname": str(docname),
                    }
        except Exception:
            pass  # Graceful degradation if domain iteration fails.
        return objects
