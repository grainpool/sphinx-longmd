project = "sphinx-longmd"
author = "Grainpool Holdings LLC"
copyright = "2026, Grainpool Holdings LLC"
release = "0.1.0"

extensions = [
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
html_theme = "alabaster"
html_static_path = ["_static"]
html_css_files = ["brand.css"]
html_title = "sphinx-longmd docs"
html_short_title = "sphinx-longmd"
html_show_sourcelink = False
html_theme_options = {
    "description": "One long-form Markdown artifact from a resolved Sphinx project.",
    "fixed_sidebar": True,
    "page_width": "1160px",
    "sidebar_width": "280px",
    "font_family": "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
    "head_font_family": "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
    "body_text_align": "left",
    "show_relbars": True,
    "github_button": False,
    "github_banner": False,
    "note_bg": "#f4f0e8",
    "note_border": "#cfc7ba",
}

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

rst_epilog = """
.. |project| replace:: sphinx-longmd
.. |company| replace:: Grainpool Holdings LLC
"""
