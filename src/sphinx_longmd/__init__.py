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
