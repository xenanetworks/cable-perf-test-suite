RX Output EQ Optimal Test
===========================================

Objective
----------

Using CMIS standard page/reg addresses, the test aims to find the transceiver output RX tap values (main, precursor, post cursor) that reduce the PRBS BER at the RX side. The test exhaust all the RX tap combinations to find the optimal settings.

Setup
----------

* The transceiver has 3 taps to adjust: amplitude, precursor and postcursor.
* Each tap has a range, ``<min>`` and ``<max>``.
* PRBS measurement duration ``<prbs_duration>``.
* Delay after EQ write ``<delay_after_eq_write>``.

Method
----------


.. figure:: ../../images/cable_test.png

    Cable performance test illustration

1. The TX port sends PRBS-31 test pattern to the RX port.
2. Try all EQ tap value combination (exhaustive search)
3. Report each PRBS BER measurement after loading a tap value combination
4. Find the EQ tap value combination that yield the lowest PRBS BER measurement.