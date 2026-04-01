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

"""Sphinx block emitters — Phase 2.

Covers admonitions, rubrics, versionmodified blocks, simple tables,
figures with captions, footnotes/citations, topics, sidebars, and
non-glossary definition lists.
"""

from __future__ import annotations

from typing import Callable

from docutils import nodes

from sphinx_longmd.context import Emission, EmissionContext


# ======================================================================
# Admonitions
# ======================================================================

_ADMONITION_TYPES = frozenset({
    "attention", "caution", "danger", "error", "hint",
    "important", "note", "tip", "warning", "seealso",
    "admonition",
})


class AdmonitionEmitter:
    """Emit admonitions as MyST colon-fenced directive blocks."""

    priority = 82

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.Admonition)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        cls_name = type(node).__name__
        if cls_name in _ADMONITION_TYPES and cls_name != "admonition":
            adm_type = cls_name
        else:
            adm_type = "admonition"

        title_text = ""
        body_children = list(node.children)
        if body_children and isinstance(body_children[0], nodes.title):
            title_node = body_children.pop(0)
            title_text = title_node.astext()

        parts: list[str] = []
        all_spans: list = []
        all_warnings: list = []
        all_losses: list = []
        for child in body_children:
            if isinstance(child, nodes.Element):
                em = visit_children(child)
            else:
                em = Emission(text=child.astext())
            parts.append(em.text)
            all_spans.extend(em.spans)
            all_warnings.extend(em.warnings)
            all_losses.extend(em.losses)
        body = "".join(parts).strip()

        if title_text and adm_type == "admonition":
            header = f":::{{admonition}} {title_text}\n"
        else:
            header = f":::{{{adm_type}}}\n"

        block = f"{header}{body}\n:::\n\n"
        return Emission(text=block, spans=all_spans,
                       warnings=all_warnings, losses=all_losses)


# ======================================================================
# Rubric
# ======================================================================

class RubricEmitter:
    priority = 82

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.rubric)

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        inner = visit_children(node)
        return Emission(text=f"**{inner.text.strip()}**\n\n", spans=inner.spans)


# ======================================================================
# Version-modified blocks
# ======================================================================

class VersionModifiedEmitter:
    priority = 82

    def matches(self, node: nodes.Node) -> bool:
        from sphinx import addnodes
        return isinstance(node, addnodes.versionmodified)

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        vtype: str = node.get("type", "changed")  # type: ignore[union-attr]
        version: str = node.get("version", "")  # type: ignore[union-attr]
        label_map = {"versionadded": "Added in", "versionchanged": "Changed in",
                     "deprecated": "Deprecated since"}
        label = label_map.get(vtype, "Changed in")
        inner = visit_children(node)
        body = inner.text.strip()
        return Emission(text=f":::{{{vtype}}}\n{label} {version}: {body}\n:::\n\n",
                       spans=inner.spans)


# ======================================================================
# Tables
# ======================================================================

class TableEmitter:
    priority = 82

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.table)

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        caption = ""
        tgroup = None
        for child in node.children:
            if isinstance(child, nodes.title):
                caption = child.astext()
            elif isinstance(child, nodes.tgroup):
                tgroup = child

        if tgroup is None:
            return visit_children(node)

        header_rows: list[list[str]] = []
        body_rows: list[list[str]] = []
        for child in tgroup.children:
            if isinstance(child, nodes.thead):
                header_rows = self._rows(child, ctx, visit_children)
            elif isinstance(child, nodes.tbody):
                body_rows = self._rows(child, ctx, visit_children)

        all_rows = header_rows + body_rows
        if not all_rows:
            return visit_children(node)

        ncols = max(len(r) for r in all_rows)
        for row in all_rows:
            while len(row) < ncols:
                row.append("")

        lines: list[str] = []
        if caption:
            lines.append(f"**{caption}**\n")

        if header_rows:
            for row in header_rows:
                lines.append("| " + " | ".join(row) + " |")
            lines.append("| " + " | ".join(["---"] * ncols) + " |")
        elif body_rows:
            first = body_rows.pop(0)
            lines.append("| " + " | ".join(first) + " |")
            lines.append("| " + " | ".join(["---"] * ncols) + " |")

        for row in body_rows:
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
        return Emission(text="\n".join(lines) + "\n")

    def _rows(self, section: nodes.Element, ctx: EmissionContext,
              visit_children: Callable[[nodes.Node], Emission]) -> list[list[str]]:
        rows: list[list[str]] = []
        for row_node in section.children:
            if isinstance(row_node, nodes.row):
                cells = []
                for entry in row_node.children:
                    if isinstance(entry, nodes.entry):
                        em = visit_children(entry)
                        cells.append(em.text.strip().replace("\n", " "))
                rows.append(cells)
        return rows


# ======================================================================
# Figures
# ======================================================================

class FigureEmitter:
    priority = 83

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.figure)

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        ids = node.get("ids", [])  # type: ignore[union-attr]
        anchor_lines = ""
        for raw_id in ids:
            emitted = ctx.anchor_registry.lookup_from_existing_id(
                ctx.current_docname, raw_id)
            anchor_lines += f'<a id="{emitted or raw_id}"></a>\n'

        image_md = ""
        caption_text = ""
        legend_text = ""
        for child in node.children:
            if isinstance(child, nodes.image):
                uri = child.get("uri", "")
                alt = child.get("alt", "")
                if hasattr(ctx.builder, "_asset_manager"):
                    out_path = ctx.builder._asset_manager.register_image(  # type: ignore[attr-defined]
                        uri, docname=ctx.current_docname)
                else:
                    out_path = uri
                image_md = f"![{alt}]({out_path})\n\n"
            elif isinstance(child, nodes.caption):
                caption_text = child.astext()
            elif isinstance(child, nodes.legend):
                em = visit_children(child)
                legend_text = em.text

        parts = [anchor_lines, image_md]
        if caption_text:
            parts.append(f"*{caption_text}*\n\n")
        if legend_text.strip():
            parts.append(legend_text)
        return Emission(text="".join(parts))


# ======================================================================
# Footnotes and citations
# ======================================================================

class FootnoteEmitter:
    priority = 82

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.footnote)

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        ids = node.get("ids", [])  # type: ignore[union-attr]
        label = ""
        body_children = list(node.children)
        if body_children and isinstance(body_children[0], nodes.label):
            label = body_children[0].astext()
            body_children = body_children[1:]
        fn_name = label or (ids[0] if ids else "fn")
        parts = []
        for child in body_children:
            if isinstance(child, nodes.Element):
                em = visit_children(child)
                parts.append(em.text.strip())
            else:
                parts.append(child.astext())
        body = " ".join(parts)
        return Emission(text=f"[^{fn_name}]: {body}\n\n")


class CitationEmitter:
    priority = 82

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.citation)

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        ids = node.get("ids", [])  # type: ignore[union-attr]
        label = ""
        body_children = list(node.children)
        if body_children and isinstance(body_children[0], nodes.label):
            label = body_children[0].astext()
            body_children = body_children[1:]
        name = label or (ids[0] if ids else "cite")
        parts = []
        for child in body_children:
            if isinstance(child, nodes.Element):
                em = visit_children(child)
                parts.append(em.text.strip())
            else:
                parts.append(child.astext())
        return Emission(text=f"[^{name}]: {' '.join(parts)}\n\n")


class FootnoteReferenceEmitter:
    priority = 78

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.footnote_reference)

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        label = node.astext()
        refid: str = node.get("refid", "")  # type: ignore[union-attr]
        return Emission(text=f"[^{label or refid or 'fn'}]")


class CitationReferenceEmitter:
    priority = 78

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.citation_reference)

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        return Emission(text=f"[^{node.astext()}]")


# ======================================================================
# Topic / sidebar
# ======================================================================

class TopicEmitter:
    priority = 78

    def matches(self, node: nodes.Node) -> bool:
        return (isinstance(node, nodes.topic)
                and "contents" not in node.get("classes", []))  # type: ignore[union-attr]

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        title = ""
        body_children = list(node.children)
        if body_children and isinstance(body_children[0], nodes.title):
            title = body_children[0].astext()
            body_children = body_children[1:]
        parts = []
        for child in body_children:
            if isinstance(child, nodes.Element):
                parts.append(visit_children(child).text)
        body = "".join(parts).strip()
        if title:
            return Emission(text=f"**{title}**\n\n{body}\n\n")
        return Emission(text=f"{body}\n\n")


class ContentsTopicEmitter:
    """Suppress local ``.. contents::`` topics."""
    priority = 88

    def matches(self, node: nodes.Node) -> bool:
        return (isinstance(node, nodes.topic)
                and "contents" in node.get("classes", []))  # type: ignore[union-attr]

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        return Emission(text="")


class SidebarEmitter:
    priority = 78

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.sidebar)

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        title = ""
        body_children = list(node.children)
        if body_children and isinstance(body_children[0], nodes.title):
            title = body_children[0].astext()
            body_children = body_children[1:]
        parts = []
        for child in body_children:
            if isinstance(child, nodes.Element):
                parts.append(visit_children(child).text)
        body = "".join(parts).strip()
        inner = f"**Sidebar — {title}**\n\n{body}" if title else body
        quoted = "\n".join(f"> {l}" if l else ">" for l in inner.split("\n"))
        return Emission(text=quoted + "\n\n")


# ======================================================================
# Definition lists (non-glossary)
# ======================================================================

class DefinitionListEmitter:
    priority = 80

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.definition_list) and not _is_glossary_list(node)

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        parts: list[str] = []
        all_spans: list = []
        for item in node.children:
            if isinstance(item, nodes.definition_list_item):
                term_text = ""
                defn_text = ""
                for child in item.children:
                    if isinstance(child, nodes.term):
                        em = visit_children(child)
                        term_text = em.text.strip()
                        all_spans.extend(em.spans)
                    elif isinstance(child, nodes.definition):
                        em = visit_children(child)
                        defn_text = em.text.strip()
                        all_spans.extend(em.spans)
                parts.append(f"{term_text}\n: {defn_text}\n")
        return Emission(text="\n".join(parts) + "\n", spans=all_spans)


def _is_glossary_list(node: nodes.Node) -> bool:
    parent = node.parent
    while parent is not None:
        if hasattr(parent, "get"):
            classes = parent.get("classes", []) or []
            if "glossary" in classes:
                return True
        if type(parent).__name__ == "glossary":
            return True
        parent = parent.parent
    return False


# ======================================================================
# Registration
# ======================================================================

def register_sphinx_block_emitters(registry: "EmitterRegistry") -> None:  # type: ignore[name-defined] # noqa: F821
    from sphinx_longmd.emit.writer import EmitterRegistry as _ER  # noqa: F811
    assert isinstance(registry, _ER)
    for cls in (
        AdmonitionEmitter, RubricEmitter, VersionModifiedEmitter,
        TableEmitter, FigureEmitter,
        FootnoteEmitter, CitationEmitter,
        FootnoteReferenceEmitter, CitationReferenceEmitter,
        TopicEmitter, ContentsTopicEmitter, SidebarEmitter,
        DefinitionListEmitter,
    ):
        registry.register(cls())  # type: ignore[arg-type]
