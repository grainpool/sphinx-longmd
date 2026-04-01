"""Doctree assembly and document-boundary helpers.

Follows the same single-file assembly pattern as Sphinx's
``SingleFileHTMLBuilder``: load the root doctree, inline all toctree
inclusions into one master tree, and resolve references on the result.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING

from docutils import nodes
from sphinx import addnodes
from sphinx.util.nodes import inline_all_toctrees

if TYPE_CHECKING:
    from sphinx_longmd.builder import LongMdBuilder

# Sphinx 9.x removed the ``darkgreen`` parameter from inline_all_toctrees.
# Detect the accepted parameters once at import time so we can call it
# correctly on any supported Sphinx version.
_INLINE_PARAMS = set(inspect.signature(inline_all_toctrees).parameters)


@dataclass(frozen=True, slots=True)
class DocBoundary:
    """Describes one inlined document's position in the assembled tree."""

    docname: str
    source_path: str | None
    node: addnodes.start_of_file | nodes.document


def assemble_master_doctree(builder: LongMdBuilder) -> nodes.document:
    """Build one master doctree rooted at ``root_doc``.

    1. Load the root doctree.
    2. Inline all ``toctree`` children using :func:`inline_all_toctrees`.
    3. Resolve references on the assembled tree.

    Returns the assembled :class:`~docutils.nodes.document`.
    """
    env = builder.env
    root_doc: str = env.config.root_doc

    master = env.get_doctree(root_doc)

    # Sphinx 9.x drastically changed the signature of inline_all_toctrees.
    # Instead of guessing, we build args/kwargs strictly from the inspected
    # parameter list.  The four positional args (builder, docnameset,
    # docname, tree) are stable across all versions.
    positional: list[object] = [builder, set(), root_doc, master]
    kwargs: dict[str, object] = {}

    # Sphinx ≤8.x
    if "darkgreen" in _INLINE_PARAMS:
        kwargs["darkgreen"] = True
    # Sphinx 9.x – colorfunc and traversed are positional
    if "colorfunc" in _INLINE_PARAMS:
        positional.append(lambda x: x)  # colorfunc – no-op
    if "traversed" in _INLINE_PARAMS:
        positional.append([])            # traversed – empty
    # Present in ≤8.x, removed in 9.x
    if "includehidden" in _INLINE_PARAMS:
        kwargs["includehidden"] = True

    master = inline_all_toctrees(*positional, **kwargs)

    master["docname"] = root_doc  # type: ignore[index]

    # Resolve cross-references within the assembled tree.
    env.resolve_references(master, root_doc, builder)

    return master


def iter_doc_boundaries(tree: nodes.document) -> list[DocBoundary]:
    """Extract document boundary markers from the assembled tree.

    The root document itself is returned first, followed by each
    ``start_of_file`` node in tree order.
    """
    root_doc: str = tree.get("docname", "index")  # type: ignore[assignment]
    source_path = _node_source(tree)

    boundaries: list[DocBoundary] = [
        DocBoundary(docname=root_doc, source_path=source_path, node=tree)
    ]

    for sof in tree.findall(addnodes.start_of_file):
        docname: str = sof.get("docname", "")  # type: ignore[assignment]
        boundaries.append(
            DocBoundary(
                docname=docname,
                source_path=_node_source(sof),
                node=sof,
            )
        )

    return boundaries


def compute_document_order(
    tree: nodes.document, root_doc: str
) -> list[str]:
    """Return the first-seen depth-first document order."""
    seen: set[str] = set()
    order: list[str] = []

    seen.add(root_doc)
    order.append(root_doc)

    for sof in tree.findall(addnodes.start_of_file):
        docname: str = sof.get("docname", "")  # type: ignore[assignment]
        if docname and docname not in seen:
            seen.add(docname)
            order.append(docname)

    return order


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _node_source(node: nodes.Node) -> str | None:
    """Best-effort source path from a node."""
    src = node.get("source")  # type: ignore[union-attr]
    if isinstance(src, str):
        return src
    if hasattr(node, "source") and isinstance(node.source, str):
        return node.source
    return None
