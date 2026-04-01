API Reference
=============

This is the API reference document, written in reStructuredText.

.. _api-overview:

Overview
--------

The API provides several utilities. See also the :ref:`intro-label` page
for getting started.

Functions
---------

The main function is ``frob()``. It accepts:

- ``x`` — first value
- ``y`` — optional second value

Example usage:

.. code-block:: python

   from demo import frob
   result = frob(1, 2)

.. image:: img/diagram.png
   :alt: Architecture diagram

Notes
-----

Some notes about the API:

1. The API is stable.
2. Breaking changes follow semver.
3. See the :doc:`intro` for background context.
