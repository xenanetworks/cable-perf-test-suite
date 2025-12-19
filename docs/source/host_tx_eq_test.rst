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

Heuristic Search Mode
^^^^^^^^^^^^^^^^^^^^^^^^
1. Start PRBS test pattern transmission from the TX port to the RX port, and measure the PRBS BER at the RX port. The measurement is set to accumulative mode to get a stable BER value after a certain duration.
2. Write the preset host TX EQ settings to the host TX EQ registers.
3. Wait for a certain duration to allow the host TX EQ settings to stabilize. Clear PRBS BER counter. Read the PRBS BER at the RX port for a certain duration, and save the last reading.
4. If the measured PRBS BER is less than or equal to the target BER, the test is complete. Else, adjust the host TX EQ settings using a heuristic algorithm to find better settings.
5. Repeat steps 2-4 until the target BER is achieved or a maximum number of iterations is reached.
6. Report each step of the adjustment process, including the host TX EQ settings and the corresponding PRBS BER.

Exhaustive Search Mode
^^^^^^^^^^^^^^^^^^^^^^^^
1. Start PRBS test pattern transmission from the TX port to the RX port, and measure the PRBS BER at the RX port. The measurement is set to accumulative mode to get a stable BER value after a certain duration.
2. Write the preset host TX EQ settings to the host TX EQ registers.
3. Wait for a certain duration to allow the host TX EQ settings to stabilize. Clear PRBS BER counter. Read the PRBS BER at the RX port for a certain duration, and save the last reading.
4. Increment each of the host Tx Eq according to the search taps list within the specified range, and repeat steps 2-3 for each combination.
5. An **exhaustive search** is performed to find the host TX EQ settings that yield **the lowest PRBS BER**. Thus, the test will repeat until all possible host TX EQ settings are tested.
6. Report each step of the adjustment process, including the host TX EQ settings and the corresponding PRBS BER.