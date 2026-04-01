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
