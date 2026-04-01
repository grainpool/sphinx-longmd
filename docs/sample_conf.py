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

# Sample conf.py for sphinx-longmd
#
# Copy the relevant sections into your project's conf.py.

# ── Required ─────────────────────────────────────────────────────────
project = "MyProject"
author = "My Team"

extensions = [
    "myst_parser",       # if you use .md sources
    "sphinx_longmd",     # the longmd builder
    # ... your other extensions ...
]

# ── Source formats ───────────────────────────────────────────────────
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# ── Optional: longmd settings ────────────────────────────────────────

# Strict mode — fail the build on unsupported nodes or unresolved refs.
# Recommended for CI pipelines. Default: False.
# longmd_strict = True

# Raw HTML policy — pass raw HTML through to the Markdown body.
# Set to False to keep the body pure Markdown (raw HTML goes to sidecar).
# Default: True.
# longmd_raw_html = False

# ── Build command ────────────────────────────────────────────────────
# sphinx-build -b longmd docs/source docs/_build/longmd
#
# Or with strict mode override:
# sphinx-build -b longmd -D longmd_strict=1 docs/source docs/_build/longmd
