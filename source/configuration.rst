Configuration
=============

The extension currently exposes a deliberately small configuration surface.

Options
-------

.. list-table::
   :header-rows: 1
   :widths: 26 14 14 46

   * - Option
     - Type
     - Default
     - Meaning
   * - ``longmd_strict``
     - ``bool``
     - ``False``
     - Fail the build on unsupported nodes or unresolved references instead of degrading gracefully.
   * - ``longmd_raw_html``
     - ``bool``
     - ``True``
     - Pass raw HTML through to the Markdown body. When disabled, raw HTML is omitted from the body and represented only in diagnostics and sidecar records.

Example ``conf.py``
-------------------

.. code-block:: python

   project = "MyProject"
   extensions = ["myst_parser", "sphinx_longmd"]

   source_suffix = {
       ".rst": "restructuredtext",
       ".md": "markdown",
   }

   # Optional but useful in CI
   longmd_strict = True

   # Optional if you want cleaner Markdown output
   longmd_raw_html = False

Recommended defaults
--------------------

For local use:

- keep ``longmd_strict = False``
- keep ``longmd_raw_html = True`` unless your downstream consumer needs cleaner Markdown

For CI or release builds:

- enable strict mode to catch custom-node regressions and unresolved references early
