Limitations and expectations
============================

This project is small, and the docs should stay honest about that. The extension does a lot for its size, but it is still a transformation layer over Sphinx internals, not a universal round-trip format.

What not to expect
------------------

Do not expect every Sphinx-only or third-party directive to survive as perfect plain Markdown. The current design prefers one of two behaviors:

- emit a reasonable Markdown or MyST representation
- degrade gracefully and record the loss in the sidecar

Known boundary conditions
-------------------------

From the implementation and tests, the current boundary lines are:

- custom or third-party nodes may fall back to a generic ``sphinx-node`` block in non-strict mode
- the same cases fail the build in strict mode
- non-HTML raw content is not emitted into the Markdown body
- output fidelity depends on how much semantic structure is available in the resolved doctree

Questions users usually ask
---------------------------

Does it support reStructuredText only?
   Yes.

Does it support MyST Markdown sources too?
   Yes, when ``myst-parser`` is installed and configured in the parent Sphinx project.

Does it preserve images?
   It copies referenced images into an ``assets/`` directory and rewrites image links to point there.

Does it preserve every internal link exactly?
   Treat internal-link behavior as practical rather than perfect. The builder is designed around stable anchors and doc-boundary IDs, but downstream consumers should still be tested against real output.

Practical scope
---------------

This documentation site is intentionally compact. For most users, the extension surface area is still:

1. install it
2. enable it
3. run ``sphinx-build -b longmd``
4. inspect the Markdown file and sidecar

However, for developers of Markdown interpreters, an additional reference document for the Markdown syntax produced by longmd is available on the following page: 'Dialect Specification'.


