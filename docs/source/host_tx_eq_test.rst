Host Tx Equalization Optimization Test
=======================================

Objective
----------

To automate manual host equalizer tuning when testing with LPO transceivers, improving efficiency and consistency in link optimization.

Setup
----------

* Host Tx equalizers preset values to load before starting the test.
* Target BER to achieve ``<target_ber>``.
* Search mode: "heuristic" or "exhaustive".
  * Heuristic: Uses an efficient algorithm to find good settings quickly, but may not find the absolute best settings.
  * Exhaustive: Tests all possible combinations of EQ settings within the specified range to find the optimal settings. More time-consuming but guarantees finding the best settings.
* EQ tap search list: a list of EQ taps to be adjusted during the test. 0 = main, -1 = pre1, -2 = pre2, -3 = pre3, 1 = post1, 2 = post2.
* PRBS measurement duration ``<duration>``.
* PRBS polynomial ``<polynomial>``.

Methodology
--------------

The principle of the test is to find the host TX equalization settings that deliver the best PRBS BER performance. The test is automated and can be run on Xena test equipment with Z800 Freya and Z1600 Edun modules.



Exhaustive Search Mode
^^^^^^^^^^^^^^^^^^^^^^^^
For pragmatic reasons, the exhaustive search mode only adjusts the specified EQ taps in the search list, while keeping other taps at their preset values. This is different from a full exhaustive search that tests all possible combinations of all EQ taps.

1. Configure PRBS pattern and measurement mode to accumulative mode.
2. Write the ``start_txeq`` to the host TX EQ registers.
3. Start PRBS test pattern transmission from the TX port to the RX port. Measure the PRBS BER at the RX port.
4. Increment each host Tx Eq in the order specified in the configuration ``optimize_txeq_ids``.
5. Each iteration finds the best BER and write the corresponding host TX EQ settings as the starting point for the next iteration.
6. If the sum of taps reaches the maximum allowed value (for Edun, the sum of all taps should not exceed 168), the iteration will stop and proceed to the next one.
7. Repeat steps 4-6 until all specified EQ taps have been adjusted.
8. Report each step of the adjustment process, including the host TX EQ settings and the corresponding PRBS BER.


Heuristic Search Mode
^^^^^^^^^^^^^^^^^^^^^^^^
1. Configure PRBS pattern and measurement mode to accumulative mode.
2. Write the ``start_txeq`` to the host TX EQ registers.
3. Start PRBS test pattern transmission from the TX port to the RX port. Measure the PRBS BER at the RX port.
4. Increment each host Tx Eq in the order specified in the configuration ``optimize_txeq_ids`` and monitor the PRBS BER after each adjustment.
5. If the measured BER is lower than the previous best BER, keep the new setting; otherwise, revert to the previous setting.
6. If the measured BER meets the target BER, the optimization of the lane is complete, and the test moves to the next lane or ends.
7. If the sum of taps reaches the maximum allowed value (for Edun, the sum of all taps should not exceed 168), the iteration will stop and proceed to the next one.
8. Repeat steps 4-7 until all specified EQ taps have been adjusted.
9. Report each step of the adjustment process, including the host TX EQ settings and the corresponding PRBS BER.