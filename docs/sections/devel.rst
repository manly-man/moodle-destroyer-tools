Development
===========

Where you can help
------------------

Backend:
  * moodle.communication: MoodleSession implements Moodle's Web Service API: it is incomplete and has no support for different service versions.
    Implementing those is tedious, especially since Moodles API is pretty wonky: You will almost always receive 200 OK, and will have to handle exceptions by hand.
  * moodle.models: contains various representations of Moodle data structures.
    They are badly interconnected and need restructuring.

Frontend:
  * wstools: needs command structure. a curses interface and better pretty printing should be nice.


Documentation
-------------

Moodle back-end
^^^^^^^^^^^^^^^

Moodle Developers do not provide direct access to the Web Service API.
The WS API Documentation is only available per Moodle instance, so you are left with some choices:

* Ask your Moodle Administrator for it,
* set-up your own Moodle Instance (I recommend you don't, installation takes a really long time),
* get it from the `Moodle Demo Server <https://moodle.org/demo/>`_,
* dig in Moodle's PHP sources (I also recommend against that, use as last resort. Does not help understanding the data structures.)

This Code
^^^^^^^^^

Well, you are reading it… That is how much documentation there is, there will be more, tho.
If you really, really want to help the tool along or ask for an explanation, ask -1 via `twitter <https://twitter.com/einsweniger/>`_ or mail.

Bootstrap
---------

Before starting to develop on manly-man moodle scripts you should run the `boostrap` script.
This will setup `git-flow` with the default settings.

We recommend `git-flow AVH Edition <https://github.com/petervanderdoes/gitflow/>`_.
For detailed installation instructions have a look at `https://github.com/petervanderdoes/gitflow/wiki <https://github.com/petervanderdoes/gitflow/wiki>`_

Working with git-flow
^^^^^^^^^^^^^^^^^^^^^

1. Start a new feature with `git-flow feature start FEATURE_NAME` (this creates a new branch)
2. Hack on your feature
3. Finish your feature with `git-flow feature stop FEATURE_NAME` (this merges the branch into `develop`)


