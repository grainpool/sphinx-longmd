Output behavior
===============

Primary artifacts
-----------------

``<root_doc>.longmd.md``
   One Markdown file containing the entire project in reading order.

``<root_doc>.longmd.map.json``
   A machine-readable sidecar with provenance and build metadata.

``assets/``
   Copied image assets with collision-safe output names.

Markdown structure
------------------

The emitted Markdown currently uses these patterns:

- ATX headings
- HTML anchors such as ``<a id="..."></a>`` for stable targets
- HTML comments to mark per-document boundaries
- standard Markdown for prose, lists, code blocks, links, and images
- MyST colon fences for semantics that do not map cleanly to plain Markdown
- fallback ``sphinx-node`` blocks for unknown custom nodes in non-strict mode

What is preserved well
----------------------

Based on the current code and tests, the builder is designed to preserve or represent:

- toctree reading order
- section and target anchors
- glossary terms
- Python domain object descriptions
- admonitions and common block-level Sphinx constructs
- figures, tables, footnotes, citations, and field lists
- copied image assets
- warnings, losses, timing, and span metadata in the sidecar

Sidecar shape
-------------

The current sidecar includes top-level keys such as:

- ``version``
- ``profile``
- ``root_doc``
- ``output_file``
- ``document_order``
- ``anchors``
- ``aliases``
- ``objects``
- ``assets``
- ``spans``
- ``warnings``
- ``losses``
- ``stats``

Anchor strategy
---------------

The builder pre-registers anchors before emission and resolves cross-document heading collisions with docname-prefixed IDs instead of numeric suffixes. That makes emitted IDs more stable when the toctree order changes.

Raw content policy
------------------

Raw HTML can pass through to the Markdown body when ``longmd_raw_html = True``. Non-HTML raw blocks are omitted from the Markdown body and recorded in the sidecar instead.
