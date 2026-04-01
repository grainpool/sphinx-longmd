"""Unit tests for the anchor registry."""

from __future__ import annotations

import pytest

from sphinx_longmd.anchors import AnchorRegistry, slugify_docname, _make_safe_id


class TestSlugifyDocname:
    def test_simple(self) -> None:
        assert slugify_docname("index") == "index"

    def test_with_slash(self) -> None:
        assert slugify_docname("api/index") == "api-index"

    def test_with_underscore_and_caps(self) -> None:
        assert slugify_docname("My_Doc") == "my-doc"


class TestMakeSafeId:
    def test_dots(self) -> None:
        assert _make_safe_id("demo.frob") == "demo-frob"

    def test_colons(self) -> None:
        assert _make_safe_id("py:function") == "py-function"


class TestAnchorRegistry:
    def test_register_and_lookup(self) -> None:
        reg = AnchorRegistry()
        rec = reg.register("doc::index", "document-index", docname="index")
        assert rec.emitted_id == "document-index"
        assert reg.emitted_id_for_canonical("doc::index") == "document-index"

    def test_collision_gets_doc_prefix(self) -> None:
        reg = AnchorRegistry()
        reg.register("doc::a", "install", docname="a")
        rec2 = reg.register("doc::b", "install", docname="b")
        # Doc-prefixed form: b--install (not numeric install-1).
        assert rec2.emitted_id == "b--install"

    def test_collision_no_docname_gets_numeric(self) -> None:
        reg = AnchorRegistry()
        reg.register("x::a", "install", docname="")
        rec2 = reg.register("x::b", "install", docname="")
        # No docname → falls back to numeric.
        assert rec2.emitted_id == "install-1"

    def test_duplicate_canonical_key_raises(self) -> None:
        reg = AnchorRegistry()
        reg.register("doc::a", "a-anchor", docname="a")
        with pytest.raises(ValueError, match="Duplicate canonical key"):
            reg.register("doc::a", "a-anchor-2", docname="a")

    def test_alias_registration(self) -> None:
        reg = AnchorRegistry()
        rec = reg.register(
            "section::intro",
            "intro",
            aliases=["intro-label", "old-intro"],
            docname="intro",
        )
        assert "intro-label" in rec.aliases
        assert "old-intro" in rec.aliases

    def test_lookup_from_existing_id(self) -> None:
        reg = AnchorRegistry()
        reg.register("intro::install", "install", docname="intro")
        assert reg.lookup_from_existing_id("intro", "install") == "install"

    def test_anchors_dict(self) -> None:
        reg = AnchorRegistry()
        reg.register("doc::index", "document-index", docname="index")
        d = reg.anchors_dict()
        assert d == {"doc::index": "document-index"}

    def test_aliases_dict(self) -> None:
        reg = AnchorRegistry()
        reg.register("x::y", "y-anchor", aliases=["old-y"], docname="x")
        d = reg.aliases_dict()
        assert d == {"old-y": "y-anchor"}

    def test_cross_doc_collision_uses_doc_prefix(self) -> None:
        """Two docs with 'see-also' sections: second gets doc-prefixed ID."""
        reg = AnchorRegistry()
        # First doc claims 'see-also'.
        r1 = reg.register("getting-started::see-also", "see-also",
                          docname="getting-started")
        assert r1.emitted_id == "see-also"

        # Second doc also has 'see-also' → gets doc-prefixed form.
        r2 = reg.register("reference/api::see-also", "see-also",
                          docname="reference/api")
        assert r2.emitted_id == "reference-api--see-also"

        # Third doc too → doc-prefix is different, so no numeric suffix.
        r3 = reg.register("tutorials/index::see-also", "see-also",
                          docname="tutorials/index")
        assert r3.emitted_id == "tutorials-index--see-also"

    def test_collision_lookup_finds_both(self) -> None:
        """After collision, both anchors resolve via lookup."""
        reg = AnchorRegistry()
        reg.register("intro::see-also", "see-also", docname="intro")
        reg.register("api::see-also", "see-also", docname="api")

        # First doc's section resolves.
        assert reg.lookup_from_existing_id("intro", "see-also") == "see-also"
        # Second doc's section also resolves (via canonical key).
        assert reg.emitted_id_for_canonical("api::see-also") == "api--see-also"

    def test_collision_ids_are_all_unique(self) -> None:
        """No two anchors ever share the same emitted ID."""
        reg = AnchorRegistry()
        ids = set()
        for i, doc in enumerate(["a", "b", "c", "d", "e"]):
            rec = reg.register(f"{doc}::overview", "overview", docname=doc)
            assert rec.emitted_id not in ids, \
                f"Duplicate emitted ID: {rec.emitted_id}"
            ids.add(rec.emitted_id)
        # First one is plain, rest are doc-prefixed.
        assert "overview" in ids
        assert "b--overview" in ids
