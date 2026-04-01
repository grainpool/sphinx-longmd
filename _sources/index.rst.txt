sphinx-longmd
==============

Export an entire Sphinx project as one long-form Markdown document, with a JSON sidecar that preserves provenance, anchors, assets, warnings, and other build metadata.

Most users only need four things: install it, enable it, run it, and understand what comes out.

.. note::

   ``sphinx-longmd`` is provided by Grainpool Holdings LLC under the `Apache License, Version 2.0 <https://github.com/grainpool/sphinx-longmd/blob/main/LICENSE>`_. Unless required by applicable law or agreed to in writing, the software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   
Background
-----------------------

|project| works from Sphinx's assembled, resolved doctree instead of raw source files or rendered HTML. That means the builder sees Sphinx after toctree expansion, cross-reference resolution, domain object registration, and substitution handling.

The result is aimed at workflows that need one portable document instead of a many-page HTML tree, such as LLM ingestion, review packets, archival exports, or downstream publishing pipelines.

Quick path
----------

Install:

.. code-block:: bash

   pip install sphinx-longmd

Enable:

.. code-block:: python

   extensions = ["sphinx_longmd"]

Run:

.. code-block:: bash

   sphinx-build -b longmd docs/source docs/_build/longmd

Expect:

.. code-block:: text

   docs/_build/longmd/
     index.longmd.md
     index.longmd.map.json
     assets/

.. toctree::
   :maxdepth: 2
   :caption: User guide

   install
   usage
   output
   configuration
   limitations   
   dialect

.. toctree::
   :maxdepth: 1
   :caption: Project

   contributing
   changelog
   license
