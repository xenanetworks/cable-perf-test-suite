Step-by-Step
=============================

Prerequisite
-------------

1. Install xoa-driver. Read `install xoa-driver <https://docs.xenanetworks.com/projects/xoa-python-api/en/latest/getting_started/index.html>`_ for details.
2. Prepare your DUT port. It is recommended that you turn off the ANLT timeout on the DUT port, if possible. This is to make sure that the timeout won't interrupt the automated test.
3. Download the scripts from `Cable Performance Test Suite GitHub Repository <https://github.com/xenanetworks/cable-perf-test-suite/>`_


Run Test
---------

There are 5 test scripts in /scripts/ directory:

* ``cable_perf_optimal.py``
* ``cable_perf_target.py``

In each script, you should set he parameters to match your test.

After setting the parameters, you can execute the script.