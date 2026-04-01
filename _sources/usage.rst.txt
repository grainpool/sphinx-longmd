Use the builder
===============

Enable the extension
--------------------

In ``conf.py``:

.. code-block:: python

   extensions = [
       "myst_parser",   # only if your docs use .md files
       "sphinx_longmd",
   ]

If your project mixes reStructuredText and Markdown, declare both source types:

.. code-block:: python

   source_suffix = {
       ".rst": "restructuredtext",
       ".md": "markdown",
   }

Build command
-------------

.. code-block:: bash

   sphinx-build -b longmd docs/source docs/_build/longmd

Strict mode from the command line:

.. code-block:: bash

   sphinx-build -b longmd -D longmd_strict=1 docs/source docs/_build/longmd

What gets exported
------------------

The builder emits one Markdown file for the whole documentation tree, ordered by the resolved toctree. It also writes a JSON sidecar and copies referenced assets into an ``assets/`` directory.

Happy-path example
------------------

Input tree:

.. code-block:: text

   docs/source/
     conf.py
     index.rst
     intro.md
     api.rst

Representative output:

.. code-block:: text

   docs/_build/longmd/
     index.longmd.md
     index.longmd.map.json
     assets/
       diagram.png

Small example from the current implementation:

.. code-block:: markdown

   <a id="document-index"></a>
   <!-- longmd:start-file docname="index" source=".../index.rst" -->

   **Contents**

   - [Index](#document-index)
   - [Intro](#document-intro)
   - [Api](#document-api)

   # TestProject

   ...

   <!-- longmd:end-file docname="index" -->

When to use it
--------------

Use |project| when you want:

- a single Markdown artifact for downstream processing
- one-file ingestion for LLM or search pipelines
- a reviewable export that keeps document order and anchor data
- a sidecar with losses, warnings, spans, and copied-asset records
