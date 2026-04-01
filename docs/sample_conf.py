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
