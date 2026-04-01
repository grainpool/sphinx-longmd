"""Structural emitters.

Covers document boundaries (``start_of_file``), sections, titles,
paragraphs, bullet/enumerated lists, block quotes, literal blocks,
and transition nodes.
"""

from __future__ import annotations

from typing import Callable

from docutils import nodes
from sphinx import addnodes

from sphinx_longmd.anchors import slugify_docname
from sphinx_longmd.context import Emission, EmissionContext, SpanRecord


# ======================================================================
# Helper
# ======================================================================

def _source_loc(node: nodes.Node, ctx: EmissionContext) -> tuple[str | None, str | None, int | None]:
    docname = ctx.current_docname
    src = node.get("source") or ctx.current_source_path  # type: ignore[union-attr]
    line = node.get("line") or (node.line if hasattr(node, "line") else None)  # type: ignore[union-attr]
    return docname, src, line  # type: ignore[return-value]


def _section_depth(node: nodes.Element) -> int:
    """Count how many ``section`` ancestors *node* has."""
    depth = 0
    parent = node.parent
    while parent is not None:
        if isinstance(parent, nodes.section):
            depth += 1
        parent = parent.parent
    return depth


# ======================================================================
# Emitters
# ======================================================================

class StartOfFileEmitter:
    """Emit ``<!-- longmd:start-file … -->`` boundaries and children."""

    priority = 100

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, addnodes.start_of_file)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        sof = node
        docname: str = sof.get("docname", "")  # type: ignore[union-attr]
        source_path: str = ctx.current_source_path or ""

        # Update current doc tracking on the context.
        prev_docname = ctx.current_docname
        prev_source = ctx.current_source_path
        prev_depth = ctx.doc_depth
        ctx.current_docname = docname
        ctx.doc_depth += 1  # child docs are one level deeper
        # Try to obtain source path from the first child section.
        for child in sof.children:
            s = child.get("source") if hasattr(child, "get") else None  # type: ignore[union-attr]
            if s:
                source_path = s
                break
        ctx.current_source_path = source_path

        doc_slug = slugify_docname(docname)

        header = (
            f'<a id="document-{doc_slug}"></a>\n'
            f'<!-- longmd:start-file docname="{docname}" source="{source_path}" -->\n\n'
        )

        body = visit_children(sof)

        footer = f'\n<!-- longmd:end-file docname="{docname}" -->\n\n'

        # Restore context.
        ctx.current_docname = prev_docname
        ctx.current_source_path = prev_source
        ctx.doc_depth = prev_depth

        return Emission(
            text=header + body.text + footer,
            spans=body.spans,
            warnings=body.warnings,
            losses=body.losses,
        )


class SectionEmitter:
    """Emit sections with ATX headings and anchors."""

    priority = 90

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.section)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        section = node
        ids: list[str] = section.get("ids", [])  # type: ignore[assignment]

        # Emit anchor(s) for the section, deduplicating resolved IDs.
        anchor_lines = ""
        seen_ids: set[str] = set()
        for raw_id in ids:
            emitted_id = ctx.anchor_registry.lookup_from_existing_id(
                ctx.current_docname, raw_id
            )
            final_id = emitted_id or raw_id
            if final_id not in seen_ids:
                seen_ids.add(final_id)
                anchor_lines += f'<a id="{final_id}"></a>\n'

        body = visit_children(section)

        return Emission(
            text=anchor_lines + body.text,
            spans=body.spans,
            warnings=body.warnings,
            losses=body.losses,
        )


class TitleEmitter:
    """Emit section titles as ATX headings.

    Heading level is determined by counting section ancestors.
    In the assembled tree, the root document title becomes ``#``,
    child document titles become ``##``, and deeper sections
    follow from there.
    """

    priority = 85

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.title) and isinstance(node.parent, nodes.section)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        section_depth = _section_depth(node)
        # section_depth counts section ancestors within the local doc tree.
        # ctx.doc_depth tracks toctree nesting (0=root, 1=child, ...).
        # Combined: root title = 1+0=1 → #, child title = 1+1=2 → ##,
        #           child subsection = 2+1=3 → ###
        level = min(max(1, section_depth + ctx.doc_depth), 6)

        inline_text = visit_children(node)
        heading = f'{"#" * level} {inline_text.text.strip()}\n\n'

        docname, src, line = _source_loc(node, ctx)
        span = SpanRecord(
            out_start_line=0,  # Placeholder – real line numbers need post-processing
            out_end_line=0,
            source_docname=docname,
            source_path=src,
            source_line=line,
            node_type="title",
        )

        return Emission(
            text=heading,
            spans=[span, *inline_text.spans],
            warnings=inline_text.warnings,
            losses=inline_text.losses,
        )


class ParagraphEmitter:
    priority = 80

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.paragraph)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        inner = visit_children(node)
        return Emission(
            text=inner.text.strip() + "\n\n",
            spans=inner.spans,
            warnings=inner.warnings,
            losses=inner.losses,
        )


class BulletListEmitter:
    priority = 80

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.bullet_list)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        parts: list[str] = []
        all_spans = []
        all_warnings = []
        all_losses = []

        for item in node.children:
            if isinstance(item, nodes.list_item):
                child_em = visit_children(item)
                text = child_em.text.strip()
                # Indent continuation lines.
                lines = text.split("\n")
                first = f"- {lines[0]}"
                rest = [f"  {l}" for l in lines[1:]]
                parts.append("\n".join([first, *rest]))
                all_spans.extend(child_em.spans)
                all_warnings.extend(child_em.warnings)
                all_losses.extend(child_em.losses)

        return Emission(
            text="\n".join(parts) + "\n\n",
            spans=all_spans,
            warnings=all_warnings,
            losses=all_losses,
        )


class EnumeratedListEmitter:
    priority = 80

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.enumerated_list)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        parts: list[str] = []
        all_spans = []
        all_warnings = []
        all_losses = []

        for i, item in enumerate(node.children, 1):
            if isinstance(item, nodes.list_item):
                child_em = visit_children(item)
                text = child_em.text.strip()
                lines = text.split("\n")
                prefix = f"{i}. "
                indent = " " * len(prefix)
                first = f"{prefix}{lines[0]}"
                rest = [f"{indent}{l}" for l in lines[1:]]
                parts.append("\n".join([first, *rest]))
                all_spans.extend(child_em.spans)
                all_warnings.extend(child_em.warnings)
                all_losses.extend(child_em.losses)

        return Emission(
            text="\n".join(parts) + "\n\n",
            spans=all_spans,
            warnings=all_warnings,
            losses=all_losses,
        )


class BlockQuoteEmitter:
    priority = 80

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.block_quote)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        inner = visit_children(node)
        quoted = "\n".join(
            f"> {line}" if line else ">"
            for line in inner.text.strip().split("\n")
        )
        return Emission(
            text=quoted + "\n\n",
            spans=inner.spans,
            warnings=inner.warnings,
            losses=inner.losses,
        )


class LiteralBlockEmitter:
    """Fenced code blocks."""

    priority = 80

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.literal_block)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        language: str = node.get("language", "")  # type: ignore[union-attr]
        if not language:
            # Sphinx may store language as a class.
            classes = node.get("classes", [])  # type: ignore[union-attr]
            for cls in classes:
                if cls and cls != "code":
                    language = cls
                    break

        text = node.astext()
        fence = "```"
        # Ensure the fence doesn't clash with content.
        while fence in text:
            fence += "`"

        return Emission(text=f"{fence}{language}\n{text}\n{fence}\n\n")


class TransitionEmitter:
    priority = 70

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.transition)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        return Emission(text="---\n\n")


class CompoundEmitter:
    """Transparent wrapper – just emit children."""

    priority = 50

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.compound)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        return visit_children(node)


class ContainerEmitter:
    """Transparent wrapper – just emit children."""

    priority = 50

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.container)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        return visit_children(node)


class ToctreeEmitter:
    """Handle toctree-related nodes.

    Bare ``addnodes.toctree`` nodes are suppressed — they are structural
    metadata, not body prose.  But ``compound[toctree-wrapper]`` nodes
    must **pass through their children**, because after
    ``inline_all_toctrees`` the inlined ``start_of_file`` nodes live
    inside that wrapper.
    """

    priority = 95

    def matches(self, node: nodes.Node) -> bool:
        if isinstance(node, addnodes.toctree):
            return True
        if (
            isinstance(node, nodes.compound)
            and "toctree-wrapper" in node.get("classes", [])  # type: ignore[union-attr]
        ):
            return True
        return False

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        # Bare toctree directive nodes are structural metadata — suppress.
        if isinstance(node, addnodes.toctree):
            return Emission(text="")
        # Compound wrapper — pass through children (start_of_file nodes).
        return visit_children(node)


class TargetEmitter:
    """Emit explicit target nodes as HTML anchors."""

    priority = 85

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.target)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        ids = node.get("ids", [])  # type: ignore[union-attr]
        parts = []
        for raw_id in ids:
            emitted = ctx.anchor_registry.lookup_from_existing_id(
                ctx.current_docname, raw_id
            )
            if emitted:
                parts.append(f'<a id="{emitted}"></a>\n')
            else:
                parts.append(f'<a id="{raw_id}"></a>\n')
        return Emission(text="".join(parts))


# ======================================================================
# Registration helper
# ======================================================================

def register_structural_emitters(registry: "EmitterRegistry") -> None:  # type: ignore[name-defined]
    from sphinx_longmd.emit.writer import EmitterRegistry as _ER  # noqa: F811

    assert isinstance(registry, _ER)
    registry.register(ToctreeEmitter())  # type: ignore[arg-type]
    registry.register(StartOfFileEmitter())  # type: ignore[arg-type]
    registry.register(SectionEmitter())  # type: ignore[arg-type]
    registry.register(TitleEmitter())  # type: ignore[arg-type]
    registry.register(ParagraphEmitter())  # type: ignore[arg-type]
    registry.register(BulletListEmitter())  # type: ignore[arg-type]
    registry.register(EnumeratedListEmitter())  # type: ignore[arg-type]
    registry.register(BlockQuoteEmitter())  # type: ignore[arg-type]
    registry.register(LiteralBlockEmitter())  # type: ignore[arg-type]
    registry.register(TransitionEmitter())  # type: ignore[arg-type]
    registry.register(CompoundEmitter())  # type: ignore[arg-type]
    registry.register(ContainerEmitter())  # type: ignore[arg-type]
    registry.register(TargetEmitter())  # type: ignore[arg-type]
