"""Inline emitters.

Handles emphasis, strong, inline literals, references (internal and
external), images, and raw text nodes.
"""

from __future__ import annotations

from typing import Callable

from docutils import nodes

from sphinx_longmd.context import Emission, EmissionContext, WarningRecord


# ======================================================================
# Text
# ======================================================================

class TextEmitter:
    priority = 10

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.Text)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        return Emission(text=node.astext())


# ======================================================================
# Inline markup
# ======================================================================

class EmphasisEmitter:
    priority = 70

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.emphasis)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        inner = visit_children(node)
        return Emission(text=f"*{inner.text}*", spans=inner.spans)


class StrongEmitter:
    priority = 70

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.strong)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        inner = visit_children(node)
        return Emission(text=f"**{inner.text}**", spans=inner.spans)


class InlineLiteralEmitter:
    priority = 70

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.literal)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        text = node.astext()
        if "`" in text:
            return Emission(text=f"`` {text} ``")
        return Emission(text=f"`{text}`")


# ======================================================================
# References / links
# ======================================================================

class ReferenceEmitter:
    """Standard external or resolved internal references."""

    priority = 75

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.reference)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        ref = node
        inner = visit_children(ref)
        text = inner.text.strip() or "link"

        # External link?
        refuri: str = ref.get("refuri", "")  # type: ignore[union-attr]
        if refuri:
            # If refuri starts with '#' it is already a same-file fragment.
            return Emission(text=f"[{text}]({refuri})")

        # Internal reference (resolved to refid or anchorname).
        refid: str = ref.get("refid", "")  # type: ignore[union-attr]
        anchorname: str = ref.get("anchorname", "")  # type: ignore[union-attr]

        if refid:
            target = ctx.anchor_registry.lookup_from_existing_id(
                ctx.current_docname, refid
            )
            if target:
                return Emission(text=f"[{text}](#{target})")
            return Emission(text=f"[{text}](#{refid})")

        if anchorname:
            frag = anchorname.lstrip("#")
            target = ctx.anchor_registry.lookup_from_existing_id(
                ctx.current_docname, frag
            )
            if target:
                return Emission(text=f"[{text}](#{target})")
            return Emission(text=f"[{text}](#{frag})")

        # Fallback: just emit the text, no link.
        return Emission(
            text=text,
            warnings=[
                WarningRecord(
                    code="unresolved_reference",
                    message=f"Reference without refuri/refid: {text!r}",
                    source_docname=ctx.current_docname,
                )
            ],
        )


class ImageEmitter:
    priority = 75

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.image)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        from sphinx_longmd.assets import AssetManager

        uri: str = node.get("uri", "")  # type: ignore[union-attr]
        alt: str = node.get("alt", "")  # type: ignore[union-attr]

        # Register with the asset manager if available on the builder.
        if hasattr(ctx.builder, "_asset_manager"):
            manager: AssetManager = ctx.builder._asset_manager  # type: ignore[attr-defined]
            out_path = manager.register_image(uri, docname=ctx.current_docname)
        else:
            out_path = uri

        return Emission(text=f"![{alt}]({out_path})\n\n")


class InlineRawEmitter:
    """Emit raw inline nodes that contain HTML."""

    priority = 40

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.raw)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        fmt: str = node.get("format", "")  # type: ignore[union-attr]
        if fmt == "html":
            return Emission(text=node.astext())
        # Non-HTML raw content – degrade.
        return Emission(
            text="",
            warnings=[
                WarningRecord(
                    code="raw_non_html",
                    message=f"Raw {fmt!r} content dropped",
                    source_docname=ctx.current_docname,
                )
            ],
        )


class TitleReferenceEmitter:
    """``title_reference`` – typically rendered like emphasis."""

    priority = 60

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.title_reference)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        inner = visit_children(node)
        return Emission(text=f"*{inner.text}*", spans=inner.spans)


class SystemMessageEmitter:
    """Suppress Sphinx/docutils system messages from body output."""

    priority = 95

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.system_message)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        return Emission(text="")


# ======================================================================
# Registration helper
# ======================================================================

def register_inline_emitters(registry: "EmitterRegistry") -> None:  # type: ignore[name-defined]
    from sphinx_longmd.emit.writer import EmitterRegistry as _ER  # noqa: F811

    assert isinstance(registry, _ER)
    registry.register(TextEmitter())  # type: ignore[arg-type]
    registry.register(EmphasisEmitter())  # type: ignore[arg-type]
    registry.register(StrongEmitter())  # type: ignore[arg-type]
    registry.register(InlineLiteralEmitter())  # type: ignore[arg-type]
    registry.register(ReferenceEmitter())  # type: ignore[arg-type]
    registry.register(ImageEmitter())  # type: ignore[arg-type]
    # Raw nodes handled by RawNodeEmitter in fallback.py (Phase 3 policy).
    registry.register(TitleReferenceEmitter())  # type: ignore[arg-type]
    registry.register(SystemMessageEmitter())  # type: ignore[arg-type]
