Object descriptions
===================

.. py:function:: demo.frob(x, y=0)

   Frob two values.

   :param x: first value
   :type x: int
   :param str y: display label
   :returns: whether export succeeded
   :rtype: bool
   :raises ValueError: duplicate anchor

.. py:class:: demo.Widget(name)

   A reusable widget component.

   :param name: widget identifier
   :type name: str

   .. py:method:: render()

      Render the widget to HTML.

      :returns: rendered HTML string
      :rtype: str

See :py:func:`demo.frob` for details.
