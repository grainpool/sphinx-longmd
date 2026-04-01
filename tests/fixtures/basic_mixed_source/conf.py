"""Minimal Sphinx conf for the basic_mixed_source fixture."""

project = "TestProject"
author = "Test Author"

root_doc = "index"

extensions = [
    "myst_parser",
    "sphinx_longmd",
]

# Allow both .rst and .md
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
