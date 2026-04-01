"""Fallback, raw-node, and comment emitters — Phase 3.

In **non-strict** mode, unrecognised nodes emit a ``:::{sphinx-node}``
colon-fenced block plus a sidecar warning/loss.

In **strict** mode (``longmd_strict = True``), encountering an
unsupported non-benign node raises :class:`StrictModeError`,
which the builder catches and reports as a deterministic build failure.
"""

from __future__ import annotations

from typing import Callable

from docutils import nodes

from sphinx_longmd.context import (
    Emission,
    EmissionContext,
    LossRecord,
    WarningRecord,
)


class StrictModeError(Exception):
    """Raised when strict mode encounters an unsupported construct."""

    def __init__(self, code: str, message: str, node_type: str = "",
                 docname: str = "", line: int | None = None) -> None:
        self.code = code
        self.node_type = node_type
        self.docname = docname
        self.line = line
        super().__init__(message)


# ------------------------------------------------------------------
# Benign-wrapper detection
# ------------------------------------------------------------------

_BENIGN_TYPES = frozenset({
    "inline", "compact_paragraph", "desc_inline", "pending",
    "substitution_reference", "comment", "decoration", "header",
    "footer", "meta", "generated", "problematic",
    "system_message",
})


def _is_benign_wrapper(node: nodes.Node) -> bool:
    return type(node).__name__ in _BENIGN_TYPES


def _node_type_str(node: nodes.Node) -> str:
    return f"{type(node).__module__}.{type(node).__qualname__}"


def _node_line(node: nodes.Node) -> int | None:
    if hasattr(node, "line") and node.line:
        return node.line  # type: ignore[return-value]
    return None


# ------------------------------------------------------------------
# Comment emitter
# ------------------------------------------------------------------

class CommentEmitter:
    """Suppress docutils comment nodes (they are not output content)."""

    priority = 90

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.comment)

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        return Emission(text="")


# ------------------------------------------------------------------
# Raw-node emitter (Phase 3 policy)
# ------------------------------------------------------------------

class RawNodeEmitter:
    """Policy-aware raw-node emitter.

    - ``raw html`` with ``longmd_raw_html=True`` → pass through.
    - ``raw html`` with ``longmd_raw_html=False`` → sidecar-only.
    - ``raw <other>`` → always sidecar-only, body omitted.
    - Strict mode + non-HTML raw → raise :class:`StrictModeError`.
    """

    priority = 42

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.raw)

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        fmt: str = node.get("format", "")  # type: ignore[union-attr]
        content = node.astext()
        docname = ctx.current_docname
        line = _node_line(node)

        if fmt == "html" and ctx.raw_html:
            return Emission(text=content)

        # Non-emittable raw content.
        if ctx.strict and fmt != "html":
            raise StrictModeError(
                code="raw_non_html_strict",
                message=f"Strict mode: raw {fmt!r} content cannot be emitted",
                node_type="raw",
                docname=docname,
                line=line,
            )

        warning = WarningRecord(
            code="raw_content_omitted",
            message=f"Raw {fmt!r} content omitted from body ({len(content)} chars)",
            severity="warning",
            source_docname=docname,
            source_line=line,
            node_type="raw",
        )
        loss = LossRecord(
            code="raw_content_sidecar_only",
            level="moderate" if fmt != "html" else "minor",
            node_type="raw",
            source_docname=docname,
            source_line=line,
            details=f"format={fmt}, length={len(content)}",
        )
        return Emission(text="", warnings=[warning], losses=[loss])


# ------------------------------------------------------------------
# Fallback emitter
# ------------------------------------------------------------------

class FallbackEmitter:
    """Catch-all for nodes that no other emitter handles.

    Priority is very low so it only fires when nothing else matches.
    """

    priority = 1

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.Element)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        node_type = _node_type_str(node)
        docname = ctx.current_docname
        source = ctx.current_source_path
        line = _node_line(node)
        benign = _is_benign_wrapper(node)

        # Benign wrappers: pass through children, no warning.
        if benign:
            return visit_children(node)

        # Non-benign unknown node.
        if ctx.strict:
            raise StrictModeError(
                code="unsupported_node_strict",
                message=(
                    f"Strict mode: no emitter for {node_type} "
                    f"(doc={docname}, line={line})"
                ),
                node_type=node_type,
                docname=docname,
                line=line,
            )

        # Non-strict: degrade gracefully.
        inner = visit_children(node)
        body_text = inner.text.strip()

        if body_text:
            block = (
                f":::{{sphinx-node}}\n"
                f":node-type: {node_type}\n"
                f":source-doc: {docname}\n"
                f":source-line: {line or ''}\n"
                f":preservation: degraded\n"
                f"\n"
                f"{body_text}\n"
                f":::\n\n"
            )
        else:
            block = ""

        warning = WarningRecord(
            code="unknown_node",
            message=f"No dedicated emitter for {node_type}",
            severity="warning",
            source_docname=docname,
            source_path=source,
            source_line=line,
            node_type=node_type,
        )
        loss = LossRecord(
            code="custom_node_degraded",
            level="moderate",
            node_type=node_type,
            source_docname=docname,
            source_path=source,
            source_line=line,
            details="emitted via sphinx-node fallback",
        )

        return Emission(
            text=block,
            spans=inner.spans,
            warnings=[warning, *inner.warnings],
            losses=[loss, *inner.losses],
        )


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------

def register_fallback_emitters(registry: "EmitterRegistry") -> None:  # type: ignore[name-defined] # noqa: F821
    from sphinx_longmd.emit.writer import EmitterRegistry as _ER  # noqa: F811
    assert isinstance(registry, _ER)
    registry.register(CommentEmitter())  # type: ignore[arg-type]
    registry.register(RawNodeEmitter())  # type: ignore[arg-type]
    registry.register(FallbackEmitter())  # type: ignore[arg-type]
