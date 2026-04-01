Contributing
============

This section is intentionally short because the codebase is focused.

Local setup
-----------

.. code-block:: bash

   git clone https://github.com/grainpool/sphinx-longmd.git
   cd sphinx-longmd
   pip install -e ".[test]"

Run tests
---------

.. code-block:: bash

   pytest tests/ -v

Or by phase:

.. code-block:: bash

   pytest tests/test_builder_smoke.py tests/test_anchors.py tests/test_assets.py tests/test_emitters.py tests/test_sidecar.py -v
   pytest tests/test_phase2.py -v
   pytest tests/test_phase3.py -v

What contributors should care about
-----------------------------------

- the builder works from the assembled doctree, not from source-text rewrites
- anchor planning happens before emission
- output changes should be checked against fixture builds, not only unit-level behavior
- degradations should be explicit and measurable in warnings, losses, or both

Suggested contributor checklist
-------------------------------

- add or update a fixture that demonstrates the behavior
- make sure the emitted Markdown still reads cleanly
- keep sidecar metadata useful when fidelity is lost
- use strict mode for confidence when touching fallback logic


