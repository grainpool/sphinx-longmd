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

"""sphinx_longmd — Sphinx builder for long-form Markdown export.

Usage::

    # conf.py
    extensions = ["sphinx_longmd"]

    # Then:
    sphinx-build -b longmd . _build/longmd
"""

from __future__ import annotations

from typing import Any

from sphinx.application import Sphinx

from sphinx_longmd.builder import LongMdBuilder

__version__ = "0.1.0"


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_builder(LongMdBuilder)

    # Phase 3 config values.
    app.add_config_value("longmd_strict", default=False, rebuild="env",
                         types=(bool,))
    app.add_config_value("longmd_raw_html", default=True, rebuild="env",
                         types=(bool,))

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": False,
    }
