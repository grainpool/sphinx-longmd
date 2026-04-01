"""Emitter registry and central line-accounting writer.

The :class:`EmitterRegistry` dispatches nodes to the highest-priority
matching :class:`NodeEmitter`.  The :func:`write_master_document` function
drives the full emission of the assembled doctree into one Markdown string,
tracking output line numbers for the sidecar.

Line accounting works as follows:

1. ``ctx.output_line_cursor`` is a 1-based counter that tracks the
   current line in the final output.
2. After each node is emitted, the writer counts newlines in the
   emitted text and stamps any ``SpanRecord`` objects whose
   ``out_start_line`` is still ``0`` (placeholder) with the actual
   output range.
3. For block-level nodes that produce non-trivial output but whose
   emitters did not create a span, the writer auto-creates one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Protocol

from docutils import nodes

from sphinx_longmd.context import Emission, EmissionContext, SpanRecord

if TYPE_CHECKING:
    pass


# Node types that warrant an automatic span when no emitter-created
# span exists.  These are the block-level constructs that a downstream
# consumer would want to map back to source.
_AUTO_SPAN_TYPES = frozenset({
    "section", "paragraph", "literal_block", "bullet_list",
    "enumerated_list", "block_quote", "table", "figure",
    "footnote", "citation", "definition_list",
    "note", "warning", "tip", "important", "hint", "caution",
    "danger", "error", "attention", "seealso", "admonition",
    "desc", "topic", "sidebar", "rubric",
    "start_of_file",
})


class NodeEmitter(Protocol):
    """Protocol for a node emitter."""

    priority: int

    def matches(self, node: nodes.Node) -> bool:
        ...

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        ...


class EmitterRegistry:
    """Priority-sorted registry of node emitters."""

    def __init__(self) -> None:
        self._emitters: list[NodeEmitter] = []

    def register(self, emitter: NodeEmitter) -> None:
        self._emitters.append(emitter)
        self._emitters.sort(key=lambda e: -e.priority)

    def find(self, node: nodes.Node) -> NodeEmitter | None:
        for em in self._emitters:
            if em.matches(node):
                return em
        return None


def _visit_children(
    node: nodes.Node,
    ctx: EmissionContext,
    registry: EmitterRegistry,
) -> Emission:
    """Recursively emit all children of *node* and concatenate results."""
    parts: list[str] = []
    all_spans: list[SpanRecord] = []
    all_warnings = []
    all_losses = []

    for child in node.children:
        child_em = _emit_node(child, ctx, registry)
        parts.append(child_em.text)
        all_spans.extend(child_em.spans)
        all_warnings.extend(child_em.warnings)
        all_losses.extend(child_em.losses)

    return Emission(
        text="".join(parts),
        spans=all_spans,
        warnings=all_warnings,
        losses=all_losses,
    )


def _node_source_info(
    node: nodes.Node,
    ctx: EmissionContext,
) -> tuple[str | None, str | None, int | None]:
    """Extract best-effort source location from a node."""
    docname = ctx.current_docname or None
    src = None
    if hasattr(node, "get"):
        src = node.get("source")  # type: ignore[union-attr]
    if not src:
        src = ctx.current_source_path
    line = None
    if hasattr(node, "get"):
        line = node.get("line")  # type: ignore[union-attr]
    if not line and hasattr(node, "line"):
        line = node.line  # type: ignore[assignment]
    return docname, src, line  # type: ignore[return-value]


def _emit_node(
    node: nodes.Node,
    ctx: EmissionContext,
    registry: EmitterRegistry,
) -> Emission:
    """Emit one node, track line numbers, stamp spans."""
    start_line = ctx.output_line_cursor

    emitter = registry.find(node)
    if emitter is None:
        emission = _visit_children(node, ctx, registry)
    else:
        emission = emitter.emit(
            node,
            ctx,
            lambda n: _visit_children(n, ctx, registry),
        )

    # Count lines in the emitted text.
    text = emission.text
    newline_count = text.count("\n")
    end_line = start_line + newline_count - 1 if newline_count > 0 else start_line

    # Advance the cursor.
    ctx.output_line_cursor = start_line + newline_count

    # Stamp any placeholder spans (out_start_line == 0).
    for span in emission.spans:
        if span.out_start_line == 0:
            span.out_start_line = start_line
            span.out_end_line = end_line

    # Auto-create a span for block-level nodes that didn't get one
    # from their emitter, if the node type is interesting and the
    # emission produced non-empty output.
    node_cls_name = type(node).__name__
    if (
        newline_count > 0
        and node_cls_name in _AUTO_SPAN_TYPES
        and not any(s.out_start_line == start_line for s in emission.spans)
    ):
        docname, src, line = _node_source_info(node, ctx)
        emission.spans.append(SpanRecord(
            out_start_line=start_line,
            out_end_line=end_line,
            source_docname=docname,
            source_path=src,
            source_line=line,
            node_type=node_cls_name,
        ))

    return emission


def write_master_document(
    tree: nodes.document,
    ctx: EmissionContext,
    registry: EmitterRegistry,
) -> str:
    """Emit the full assembled doctree and return the Markdown text.

    Side-effects: updates ``ctx.spans``, ``ctx.warnings``, ``ctx.losses``,
    and ``ctx.output_line_cursor``.
    """
    emission = _visit_children(tree, ctx, registry)

    # Accumulate provenance into the context.
    ctx.spans.extend(emission.spans)
    ctx.warnings.extend(emission.warnings)
    ctx.losses.extend(emission.losses)

    # Ensure trailing newline.
    text = emission.text
    if text and not text.endswith("\n"):
        text += "\n"

    return text
