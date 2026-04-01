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

"""Unit tests for sidecar serialisation."""

from __future__ import annotations

import json
from pathlib import Path

from sphinx_longmd.context import LossRecord, SpanRecord, WarningRecord
from sphinx_longmd.sidecar import SidecarModel


class TestSidecarModel:
    def test_to_dict_has_required_keys(self) -> None:
        m = SidecarModel(root_doc="index", output_file="index.longmd.md")
        d = m.to_dict()
        for key in ("version", "profile", "root_doc", "output_file",
                     "document_order", "anchors", "spans", "warnings", "stats"):
            assert key in d, f"Missing required key: {key}"

    def test_add_spans(self) -> None:
        m = SidecarModel()
        m.add_spans([
            SpanRecord(out_start_line=1, out_end_line=5, node_type="title"),
        ])
        assert len(m.spans) == 1
        assert m.spans[0]["out_start_line"] == 1

    def test_add_warnings(self) -> None:
        m = SidecarModel()
        m.add_warnings([
            WarningRecord(code="test", message="Test warning"),
        ])
        assert len(m.warnings) == 1

    def test_add_losses(self) -> None:
        m = SidecarModel()
        m.add_losses([
            LossRecord(code="custom_node_degraded", node_type="Foo"),
        ])
        assert len(m.losses) == 1

    def test_write_and_read(self, tmp_path: Path) -> None:
        m = SidecarModel(
            root_doc="index",
            output_file="index.longmd.md",
            document_order=["index", "intro"],
        )
        path = tmp_path / "test.map.json"
        m.write(path)
        data = json.loads(path.read_text())
        assert data["root_doc"] == "index"
        assert data["document_order"] == ["index", "intro"]
