# cable-perf-test-suite

This repo contains three scripts:
* ``cable_perf_optimal.py`` uses exhaustive search to measure the PRBS BER on each transceiver cursor value combination. At the end, all results are sorted based on PRBS BER value with the best one on the top.
* ``cable_perf_target.py`` uses a target value to find the locally optimal transceiver cursor value combination. When the measured PRBS BER value is less that the target, the search will stop.
* ``eq_rw_example.py`` shows you how to do EQ read and write.

