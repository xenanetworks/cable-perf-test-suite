Step-by-Step
=============================

Prerequisite
-------------

1. Install tdl-xoa-driver. Read `install tdl-xoa-driver <https://docs.xenanetworks.com/projects/tdl-xoa-driver/en/latest/getting_started/index.html>`_ for details.
2. Prepare your DUT port. It is recommended that you turn off the ANLT timeout on the DUT port, if possible. This is to make sure that the timeout won't interrupt the automated test.
3. Download the scripts from `Cable Performance Test Suite GitHub Repository <https://github.com/xenanetworks/cable-perf-test-suite/>`_


Run Test
---------

Test scripts can be found in /scripts/ directory:

* ``prbs_perf_optimal.py``, see :doc:`cable_perf_tests/rx_output_eq_tests/rx_output_eq_optimal`
* ``prbs_perf_target.py``, see :doc:`cable_perf_tests/rx_output_eq_tests/rx_output_eq_target`

In each script, you should set he parameters to match your test.

After setting the parameters, you can execute the script.