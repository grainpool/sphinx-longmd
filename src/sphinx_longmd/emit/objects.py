"""Object-description, glossary, and field-list emitters — Phase 2.

Covers the ``addnodes.desc`` family (Python domain objects etc.),
glossary terms, and field lists with API info-field normalisation.
"""

from __future__ import annotations

from typing import Callable

from docutils import nodes
from sphinx import addnodes

from sphinx_longmd.context import Emission, EmissionContext


# ======================================================================
# Object descriptions (desc family)
# ======================================================================

class DescEmitter:
    """Emit Sphinx object descriptions as MyST colon-fenced directive blocks.

    Shape::

        <a id="py-function-demo.frob"></a>
        :::{py:function} demo.frob(x, y=0)
        :source-doc: api/index

        Body content with normalised field lists.
        :::
    """

    priority = 88

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, addnodes.desc)

    def emit(
        self,
        node: nodes.Node,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        desc_node = node
        domain: str = desc_node.get("domain", "")  # type: ignore[union-attr]
        objtype: str = desc_node.get("objtype", "")  # type: ignore[union-attr]

        # Collect signatures and content.
        signatures: list[str] = []
        sig_ids: list[str] = []
        content_emission = Emission(text="")

        for child in desc_node.children:
            if isinstance(child, addnodes.desc_signature):
                sig_text = child.astext().strip()
                signatures.append(sig_text)
                ids = child.get("ids", [])
                sig_ids.extend(ids)
            elif isinstance(child, addnodes.desc_content):
                content_emission = self._emit_desc_content(child, ctx, visit_children)

        if not signatures:
            return visit_children(desc_node)

        # Emit anchors.
        anchor_lines = ""
        seen_anchors: set[str] = set()
        for raw_id in sig_ids:
            emitted = ctx.anchor_registry.lookup_from_existing_id(
                ctx.current_docname, raw_id
            )
            aid = emitted or raw_id
            if aid not in seen_anchors:
                seen_anchors.add(aid)
                anchor_lines += f'<a id="{aid}"></a>\n'

        # Build directive block.
        primary_sig = signatures[0]
        directive_name = f"{domain}:{objtype}" if domain and objtype else "object"

        block = f"{anchor_lines}:::{{{directive_name}}} {primary_sig}\n"
        block += f":source-doc: {ctx.current_docname}\n"

        # Additional signatures as extra lines.
        for sig in signatures[1:]:
            block += f":sig: {sig}\n"

        block += f"\n{content_emission.text.strip()}\n:::\n\n"

        return Emission(
            text=block,
            spans=content_emission.spans,
            warnings=content_emission.warnings,
            losses=content_emission.losses,
        )

    def _emit_desc_content(
        self,
        content_node: addnodes.desc_content,
        ctx: EmissionContext,
        visit_children: Callable[[nodes.Node], Emission],
    ) -> Emission:
        """Emit the desc_content block.

        Delegates to ``visit_children`` which dispatches each child
        through the emitter registry.  This ensures nested ``desc``
        nodes (e.g. methods inside a class) are handled by
        ``DescEmitter``, and field lists are handled by
        ``FieldListEmitter`` (which detects the desc context).
        """
        return visit_children(content_node)


class DescSignatureEmitter:
    """Prevent desc_signature from being handled by the fallback."""

    priority = 87

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, addnodes.desc_signature)

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        # Handled by DescEmitter; should not appear standalone.
        return Emission(text="")


class DescContentEmitter:
    """Prevent desc_content from being handled by the fallback."""

    priority = 87

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, addnodes.desc_content)

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        return visit_children(node)


# ======================================================================
# Inline desc nodes (suppress fallback for these)
# ======================================================================

class DescNameEmitter:
    """Pass through desc_name, desc_addname, desc_annotation, etc."""

    priority = 75

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, (
            addnodes.desc_name, addnodes.desc_addname,
            addnodes.desc_annotation, addnodes.desc_returns,
            addnodes.desc_parameterlist, addnodes.desc_parameter,
            addnodes.desc_optional,
        ))

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        return visit_children(node)


class DescTypeEmitter:
    """desc_type and desc_sig_* nodes — pass text through."""

    priority = 74

    def matches(self, node: nodes.Node) -> bool:
        cls_name = type(node).__name__
        return cls_name.startswith("desc_sig_") or cls_name == "desc_type"

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        return visit_children(node)


# ======================================================================
# Field lists
# ======================================================================

class FieldListEmitter:
    """Emit field lists — normalising API info fields when inside desc_content.

    When outside object descriptions, renders as a simple definition-list
    or bold-label structure.
    """

    priority = 81

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.field_list)

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        # If inside a desc_content, DescEmitter handles this; but if the
        # field list appears standalone, render as bold labels.
        if _inside_desc(node):
            return _emit_normalized_field_list(node, ctx, visit_children)
        return _emit_generic_field_list(node, ctx, visit_children)


def _inside_desc(node: nodes.Node) -> bool:
    parent = node.parent
    while parent is not None:
        if isinstance(parent, addnodes.desc_content):
            return True
        parent = parent.parent
    return False


def _emit_generic_field_list(
    node: nodes.field_list,
    ctx: EmissionContext,
    visit_children: Callable[[nodes.Node], Emission],
) -> Emission:
    """Render a generic field list as bold-label paragraphs."""
    parts: list[str] = []
    for field in node.children:
        if isinstance(field, nodes.field):
            name = ""
            body = ""
            for child in field.children:
                if isinstance(child, nodes.field_name):
                    name = child.astext()
                elif isinstance(child, nodes.field_body):
                    em = visit_children(child)
                    body = em.text.strip()
            parts.append(f"**{name}:** {body}\n\n")
    return Emission(text="".join(parts))


def _emit_normalized_field_list(
    node: nodes.field_list,
    ctx: EmissionContext,
    visit_children: Callable[[nodes.Node], Emission],
) -> Emission:
    """Normalise API info fields into structured sections.

    Handles two cases:
    1. Sphinx pre-processed fields — field names are already "Parameters",
       "Returns", "Raises", etc. with structured bodies.
    2. Raw info fields — field names are "param x", "type x", "rtype", etc.
    """
    # First, check if Sphinx already pre-processed the fields into
    # section-style names like "Parameters", "Returns", "Raises".
    _SECTION_NAMES = {
        "Parameters", "Keyword Arguments", "Other Parameters",
        "Returns", "Return type", "Yields", "Raises",
        "Attributes", "Variables",
    }

    field_names: list[str] = []
    for field in node.children:
        if isinstance(field, nodes.field):
            for child in field.children:
                if isinstance(child, nodes.field_name):
                    field_names.append(child.astext())

    if any(fn in _SECTION_NAMES for fn in field_names):
        # Pre-processed by Sphinx domain — emit section headers + body.
        parts: list[str] = []
        for field in node.children:
            if not isinstance(field, nodes.field):
                continue
            name = ""
            body_em = Emission(text="")
            for child in field.children:
                if isinstance(child, nodes.field_name):
                    name = child.astext()
                elif isinstance(child, nodes.field_body):
                    body_em = visit_children(child)
            body = body_em.text.strip()
            parts.append(f"**{name}**\n{body}\n\n")
        return Emission(text="".join(parts))

    # Raw info fields — parse and group them.
    params: list[dict[str, str]] = []
    kwargs: list[dict[str, str]] = []
    returns: list[dict[str, str]] = []
    yields: list[dict[str, str]] = []
    raises: list[dict[str, str]] = []
    attrs: list[dict[str, str]] = []
    other: list[tuple[str, str]] = []

    for field in node.children:
        if not isinstance(field, nodes.field):
            continue
        name = ""
        body = ""
        for child in field.children:
            if isinstance(child, nodes.field_name):
                name = child.astext()
            elif isinstance(child, nodes.field_body):
                em = visit_children(child)
                body = em.text.strip()

        parsed = _parse_info_field(name, body)
        if parsed is None:
            other.append((name, body))
            continue

        kind = parsed["kind"]
        if kind == "param":
            _merge_param(params, parsed)
        elif kind == "type":
            _merge_type(params, parsed)
        elif kind == "keyword":
            _merge_param(kwargs, parsed)
        elif kind == "kwtype":
            _merge_type(kwargs, parsed)
        elif kind in ("returns", "rtype"):
            if kind == "rtype":
                if returns:
                    returns[-1]["type"] = parsed.get("type_str", "")
                else:
                    returns.append({"type": parsed.get("type_str", ""), "desc": ""})
            else:
                returns.append({"type": "", "desc": parsed.get("desc", "")})
        elif kind in ("yields", "ytype"):
            if kind == "ytype":
                if yields:
                    yields[-1]["type"] = parsed.get("type_str", "")
                else:
                    yields.append({"type": parsed.get("type_str", ""), "desc": ""})
            else:
                yields.append({"type": "", "desc": parsed.get("desc", "")})
        elif kind == "raises":
            raises.append({"type": parsed.get("exc_type", ""), "desc": parsed.get("desc", "")})
        elif kind in ("ivar", "vartype", "cvar"):
            if kind == "vartype":
                _merge_type(attrs, parsed)
            else:
                _merge_param(attrs, parsed)
        else:
            other.append((name, body))

    # Render sections.
    parts2: list[str] = []
    if params:
        parts2.append("**Parameters**\n")
        for p in params:
            parts2.append(_format_param_line(p))
        parts2.append("\n")
    if kwargs:
        parts2.append("**Keyword Arguments**\n")
        for p in kwargs:
            parts2.append(_format_param_line(p))
        parts2.append("\n")
    if attrs:
        parts2.append("**Attributes**\n")
        for p in attrs:
            parts2.append(_format_param_line(p))
        parts2.append("\n")
    if returns:
        parts2.append("**Returns**\n")
        for r in returns:
            parts2.append(_format_return_line(r))
        parts2.append("\n")
    if yields:
        parts2.append("**Yields**\n")
        for y in yields:
            parts2.append(_format_return_line(y))
        parts2.append("\n")
    if raises:
        parts2.append("**Raises**\n")
        for r in raises:
            exc = r.get("type", "")
            desc = r.get("desc", "")
            if exc:
                parts2.append(f"- `{exc}`: {desc}\n")
            else:
                parts2.append(f"- {desc}\n")
        parts2.append("\n")
    if other:
        for name, body in other:
            parts2.append(f"**{name}:** {body}\n\n")

    return Emission(text="".join(parts2))


def _parse_info_field(name: str, body: str) -> dict[str, str] | None:
    """Parse a field name like ``param int x`` or ``raises ValueError``."""
    parts = name.split()
    if not parts:
        return None

    keyword = parts[0].rstrip(":")
    rest = parts[1:]

    mapping: dict[str, str] = {
        "param": "param", "parameter": "param", "arg": "param",
        "type": "type",
        "keyword": "keyword", "kwarg": "keyword",
        "kwtype": "kwtype",
        "returns": "returns", "return": "returns",
        "rtype": "rtype", "returntype": "rtype",
        "yields": "yields", "yield": "yields",
        "ytype": "ytype",
        "raises": "raises", "raise": "raises", "except": "raises", "exception": "raises",
        "ivar": "ivar", "var": "ivar",
        "vartype": "vartype",
        "cvar": "cvar",
    }

    kind = mapping.get(keyword)
    if kind is None:
        return None

    result: dict[str, str] = {"kind": kind}

    if kind == "param":
        if len(rest) >= 2:
            result["type_str"] = rest[0]
            result["name"] = rest[1]
        elif len(rest) == 1:
            result["name"] = rest[0]
        result["desc"] = body
    elif kind == "type":
        result["name"] = rest[0] if rest else ""
        result["type_str"] = body
    elif kind == "keyword":
        if len(rest) >= 2:
            result["type_str"] = rest[0]
            result["name"] = rest[1]
        elif len(rest) == 1:
            result["name"] = rest[0]
        result["desc"] = body
    elif kind == "kwtype":
        result["name"] = rest[0] if rest else ""
        result["type_str"] = body
    elif kind in ("returns", "yields"):
        result["desc"] = body
    elif kind in ("rtype", "ytype"):
        result["type_str"] = body
    elif kind == "raises":
        result["exc_type"] = rest[0] if rest else ""
        result["desc"] = body
    elif kind in ("ivar", "cvar"):
        if len(rest) >= 2:
            result["type_str"] = rest[0]
            result["name"] = rest[1]
        elif len(rest) == 1:
            result["name"] = rest[0]
        result["desc"] = body
    elif kind == "vartype":
        result["name"] = rest[0] if rest else ""
        result["type_str"] = body

    return result


def _merge_param(params: list[dict[str, str]], parsed: dict[str, str]) -> None:
    name = parsed.get("name", "")
    for p in params:
        if p.get("name") == name:
            if "type_str" in parsed and parsed["type_str"]:
                p["type"] = parsed["type_str"]
            if "desc" in parsed and parsed["desc"]:
                p["desc"] = parsed["desc"]
            return
    entry: dict[str, str] = {"name": name, "desc": parsed.get("desc", "")}
    if "type_str" in parsed:
        entry["type"] = parsed["type_str"]
    params.append(entry)


def _merge_type(params: list[dict[str, str]], parsed: dict[str, str]) -> None:
    name = parsed.get("name", "")
    type_str = parsed.get("type_str", "")
    for p in params:
        if p.get("name") == name:
            p["type"] = type_str
            return
    params.append({"name": name, "type": type_str, "desc": ""})


def _format_param_line(p: dict[str, str]) -> str:
    name = p.get("name", "")
    typ = p.get("type", "")
    desc = p.get("desc", "")
    if typ and desc:
        return f"- `{name}` (`{typ}`): {desc}\n"
    elif typ:
        return f"- `{name}` (`{typ}`)\n"
    elif desc:
        return f"- `{name}`: {desc}\n"
    return f"- `{name}`\n"


def _format_return_line(r: dict[str, str]) -> str:
    typ = r.get("type", "")
    desc = r.get("desc", "")
    if typ and desc:
        return f"- `{typ}`: {desc}\n"
    elif typ:
        return f"- `{typ}`\n"
    return f"- {desc}\n"


# ======================================================================
# Glossary
# ======================================================================

class GlossaryEmitter:
    """Emit glossary containers — delegates to GlossaryListEmitter."""

    priority = 84

    def matches(self, node: nodes.Node) -> bool:
        from sphinx import addnodes as _an
        return hasattr(_an, "glossary") and isinstance(node, _an.glossary)

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        return visit_children(node)


class GlossaryListEmitter:
    """Emit glossary definition lists with anchored terms."""

    priority = 84

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, nodes.definition_list) and _is_glossary_list(node)

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        parts: list[str] = []
        for item in node.children:
            if not isinstance(item, nodes.definition_list_item):
                continue
            for child in item.children:
                if isinstance(child, nodes.term):
                    term_text = child.astext().strip()
                    term_ids = child.get("ids", [])
                    # Emit anchor for the term.
                    for tid in term_ids:
                        emitted = ctx.anchor_registry.lookup_from_existing_id(
                            ctx.current_docname, tid)
                        parts.append(f'<a id="{emitted or tid}"></a>\n')
                    parts.append(f"**{term_text}**\n")
                elif isinstance(child, nodes.definition):
                    em = visit_children(child)
                    defn = em.text.strip()
                    parts.append(f": {defn}\n\n")
        return Emission(text="".join(parts))


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
# Pending xref (leftover unresolved cross-references)
# ======================================================================

class PendingXrefEmitter:
    """Emit unresolved pending_xref nodes as readable text + warning."""

    priority = 76

    def matches(self, node: nodes.Node) -> bool:
        return isinstance(node, addnodes.pending_xref)

    def emit(self, node: nodes.Node, ctx: EmissionContext,
             visit_children: Callable[[nodes.Node], Emission]) -> Emission:
        from sphinx_longmd.context import WarningRecord
        inner = visit_children(node)
        text = inner.text.strip()
        reftarget = node.get("reftarget", "")  # type: ignore[union-attr]
        refdomain = node.get("refdomain", "")  # type: ignore[union-attr]
        reftype = node.get("reftype", "")  # type: ignore[union-attr]

        # Try to find the target in the anchor registry.
        if reftarget:
            emitted = ctx.anchor_registry.lookup_from_existing_id(
                ctx.current_docname, str(reftarget))
            if emitted:
                return Emission(text=f"[{text or reftarget}](#{emitted})")

        warning = WarningRecord(
            code="unresolved_xref",
            message=f"Unresolved {refdomain}:{reftype} reference to {reftarget!r}",
            source_docname=ctx.current_docname,
        )
        display = text or str(reftarget) or "?"
        return Emission(text=f"`{display}`", warnings=[warning])


# ======================================================================
# Registration
# ======================================================================

def register_object_emitters(registry: "EmitterRegistry") -> None:  # type: ignore[name-defined] # noqa: F821
    from sphinx_longmd.emit.writer import EmitterRegistry as _ER  # noqa: F811
    assert isinstance(registry, _ER)
    for cls in (
        DescEmitter, DescSignatureEmitter, DescContentEmitter,
        DescNameEmitter, DescTypeEmitter,
        FieldListEmitter,
        GlossaryEmitter, GlossaryListEmitter,
        PendingXrefEmitter,
    ):
        registry.register(cls())  # type: ignore[arg-type]
