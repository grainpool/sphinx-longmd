"""Fake extension that defines a custom node for testing fallback behavior."""

from __future__ import annotations

from typing import Any

from docutils import nodes
from sphinx.application import Sphinx


class custom_card(nodes.General, nodes.Element):
    """A third-party card node with no dedicated emitter."""
    pass


def visit_noop(self: Any, node: custom_card) -> None:
    pass


def depart_noop(self: Any, node: custom_card) -> None:
    pass


def card_role(name: str, rawtext: str, text: str, lineno: int,
              inliner: Any, options: dict | None = None,
              content: list | None = None) -> tuple:
    node = custom_card()
    node += nodes.paragraph("", text)
    return [node], []


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_node(custom_card,
                 html=(visit_noop, depart_noop),
                 text=(visit_noop, depart_noop))
    app.add_role("card", card_role)
    return {"version": "0.1", "parallel_read_safe": True}
