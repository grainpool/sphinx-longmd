"""Unit tests for the asset manager."""

from __future__ import annotations

from sphinx_longmd.assets import AssetManager


class TestAssetManager:
    def test_register_image(self) -> None:
        mgr = AssetManager()
        path = mgr.register_image("img/diagram.png", docname="api")
        assert path == "assets/diagram.png"

    def test_deduplicates_same_uri(self) -> None:
        mgr = AssetManager()
        p1 = mgr.register_image("img/logo.png")
        p2 = mgr.register_image("img/logo.png")
        assert p1 == p2
        assert len(mgr.all_records()) == 1

    def test_collision_different_dirs(self) -> None:
        mgr = AssetManager()
        p1 = mgr.register_image("a/logo.png")
        p2 = mgr.register_image("b/logo.png")
        assert p1 != p2
        assert "logo" in p2
        assert len(mgr.all_records()) == 2
