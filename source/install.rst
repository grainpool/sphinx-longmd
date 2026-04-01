Install
=======

Published package
-----------------

.. code-block:: bash

   pip install sphinx-longmd

If your Sphinx project includes Markdown source files, also install MyST support:

.. code-block:: bash

   pip install sphinx-longmd myst-parser

Development install
-------------------

.. code-block:: bash

   git clone https://github.com/grainpool/sphinx-longmd.git
   cd sphinx-longmd
   pip install -e ".[test]"

Minimum expectations
--------------------

- Python 3.11+
- Sphinx 9.x
- MyST-Parser only when your docs include ``.md`` source files
