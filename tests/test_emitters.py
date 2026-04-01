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

"""Unit tests for individual emitters.

These tests construct minimal docutils nodes and verify the emitted
Markdown text, without requiring a full Sphinx build.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# These tests require sphinx and docutils; skip if not installed.
sphinx = pytest.importorskip("sphinx")
nodes_mod = pytest.importorskip("docutils.nodes")

from docutils import nodes

from sphinx_longmd.anchors import AnchorRegistry
from sphinx_longmd.context import Emission, EmissionContext
from sphinx_longmd.sidecar import SidecarModel
from sphinx_longmd.emit.writer import EmitterRegistry
from sphinx_longmd.emit.structural import (
    ParagraphEmitter,
    BulletListEmitter,
    EnumeratedListEmitter,
    BlockQuoteEmitter,
    LiteralBlockEmitter,
    TitleEmitter,
)
from sphinx_longmd.emit.inline import (
    TextEmitter,
    EmphasisEmitter,
    StrongEmitter,
    InlineLiteralEmitter,
)


def _make_ctx() -> EmissionContext:
    """Build a minimal EmissionContext for unit testing."""
    builder = MagicMock()
    env = MagicMock()
    tree = MagicMock()
    reg = AnchorRegistry()
    sidecar = SidecarModel()
    return EmissionContext(
        builder=builder,
        env=env,
        root_doc="index",
        assembled_doctree=tree,
        anchor_registry=reg,
        sidecar=sidecar,
        current_docname="test",
    )


def _visit_children_text(node: nodes.Node) -> Emission:
    """Simple child visitor that just concatenates text."""
    parts = []
    for child in node.children:
        if isinstance(child, nodes.Text):
            parts.append(child.astext())
        else:
            parts.append(_visit_children_text(child).text)
    return Emission(text="".join(parts))


class TestParagraphEmitter:
    def test_simple_paragraph(self) -> None:
        ctx = _make_ctx()
        p = nodes.paragraph("", "", nodes.Text("Hello world"))
        em = ParagraphEmitter()
        result = em.emit(p, ctx, _visit_children_text)
        assert result.text == "Hello world\n\n"


class TestEmphasisEmitter:
    def test_emphasis(self) -> None:
        ctx = _make_ctx()
        node = nodes.emphasis("", "", nodes.Text("italic"))
        em = EmphasisEmitter()
        result = em.emit(node, ctx, _visit_children_text)
        assert result.text == "*italic*"


class TestStrongEmitter:
    def test_strong(self) -> None:
        ctx = _make_ctx()
        node = nodes.strong("", "", nodes.Text("bold"))
        em = StrongEmitter()
        result = em.emit(node, ctx, _visit_children_text)
        assert result.text == "**bold**"


class TestInlineLiteralEmitter:
    def test_literal(self) -> None:
        ctx = _make_ctx()
        node = nodes.literal("", "code_here")
        em = InlineLiteralEmitter()
        result = em.emit(node, ctx, _visit_children_text)
        assert result.text == "`code_here`"

    def test_literal_with_backtick(self) -> None:
        ctx = _make_ctx()
        node = nodes.literal("", "co`de")
        em = InlineLiteralEmitter()
        result = em.emit(node, ctx, _visit_children_text)
        assert result.text == "`` co`de ``"


class TestBulletListEmitter:
    def test_bullet_list(self) -> None:
        ctx = _make_ctx()
        items = [
            nodes.list_item("", nodes.paragraph("", "", nodes.Text("one"))),
            nodes.list_item("", nodes.paragraph("", "", nodes.Text("two"))),
        ]
        bl = nodes.bullet_list("", *items)
        em = BulletListEmitter()
        result = em.emit(bl, ctx, _visit_children_text)
        assert "- one" in result.text
        assert "- two" in result.text


class TestEnumeratedListEmitter:
    def test_enum_list(self) -> None:
        ctx = _make_ctx()
        items = [
            nodes.list_item("", nodes.paragraph("", "", nodes.Text("first"))),
            nodes.list_item("", nodes.paragraph("", "", nodes.Text("second"))),
        ]
        el = nodes.enumerated_list("", *items)
        em = EnumeratedListEmitter()
        result = em.emit(el, ctx, _visit_children_text)
        assert "1. first" in result.text
        assert "2. second" in result.text


class TestBlockQuoteEmitter:
    def test_block_quote(self) -> None:
        ctx = _make_ctx()
        bq = nodes.block_quote("", nodes.paragraph("", "", nodes.Text("quoted text")))
        em = BlockQuoteEmitter()
        result = em.emit(bq, ctx, _visit_children_text)
        assert "> quoted text" in result.text


class TestLiteralBlockEmitter:
    def test_code_block(self) -> None:
        ctx = _make_ctx()
        cb = nodes.literal_block("print('hi')", "print('hi')")
        cb["language"] = "python"
        em = LiteralBlockEmitter()
        result = em.emit(cb, ctx, _visit_children_text)
        assert "```python" in result.text
        assert "print('hi')" in result.text
        assert result.text.strip().endswith("```")
