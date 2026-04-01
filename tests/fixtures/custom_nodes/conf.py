import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "_ext"))

project = "Phase3Test"
author = "Test"
root_doc = "index"
extensions = ["myst_parser", "sphinx_longmd", "fake_card"]
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
