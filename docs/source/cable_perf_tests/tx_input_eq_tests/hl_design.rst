TX Input EQ Test Design
========================


Principle Flow
---------------

The principle of all the tests is to find the RX Ouput EQ settings that reduce the PRBS bit error rate to satisfy a critera. The tests are based on the CMIS standard page/reg addresses. The tests are automated and can be run on Xena test equipment with Z800 Freya modules.

1. Check if the transceiver module supports the EQ control as described in `TX Input EQ Advertisement`_.

    * If the transceiver module supports EQ control, the test can be run. Else, the test will abort.

2. Start PRBS-31 test pattern transmission from the TX port to the RX port, and measure the PRBS BER at the RX port. The measurement is set to accumulative mode to get a stable BER value after a certain duration.
3. Deinitialize the Data Path associated with host lane. All lanes of a Data Path must have the same value. This is implemented by writing ``Page 10h Register 128`` with value ``0xFF``.
4. Read Data Path Configuration of each lane. This is implemented by reading ``Page 10h Register 145 - 152``. The purpose is to cache the ``AppSelCode`` and ``DataPathID`` values because we don't want to change them during the test. What we want to change is the ``ExplicitControl`` bit.
5. Write the RX output EQ settings to the RX Output EQ registers. This is implemented by writing ``Page 10h Register 162 - 173``. Depending on the search algorithm, optimal or target, the sequence of RX output EQ writing can be different.
6. Write the Explicit Control bit to 1. This is implemented by writing ``Page 10h Register 145 - 152`` with the cached ``AppSelCode`` and ``DataPathID`` values and the ``ExplicitControl`` bit set to 1.
7. Trigger the Provision procedure via an ``ApplyDPInit`` register ``Page 10h Register 143`` by writing ``0xFF``.
8. Activate the Data Path associated with the host lane. This is implemented by writing ``Page 10h Register 128`` with value ``0x00``.
9. Wait for a certain duration to let the EQ settings take effect.
10. Clear PRBS BER counter. Read the PRBS BER at the RX port for a certain duration, and save the last reading.
11. For the optimal test, an exhaustive search is performed to find the RX output EQ settings that yield the lowest PRBS BER. Thus, the test will repeat Step 3 - 10 for all possible RX output EQ settings. 
12. For the target test, an iterative algorithm will find the RX output EQ settings that satisfy the target BER criteria, not necessarily the lowest BER. Thus, the test will repeat Step 3 - 10 until the target BER criteria is satisfied.

.. figure:: ../../images/cmis_control_set_data_flow.png

    CMIS Control Set Data Flow


TX Equalizer Control
---------------------

TX EQ (TX input equalizer control) settings can be either FIXED or ADAPTIVE. For TX input, only adaptive EQ should be used, and it is the default setting in the module. Fixed EQ is not recommended for the TX direction and will not function correctly unless explicitly advised.

.. _cmis_tx_eq_support:

.. figure:: ../../images/cmis_tx_eq_support.png

    TX Input EQ Advertisement

If the ``TxInputEqFixedManualControlSupported`` flag is set, as defined in :numref:`cmis_tx_eq_support`, then the module supports host-controlled Tx input equalization. In this case, the host can control the Tx input equalization settings. If the flag is not set, then the module does not support host-controlled Tx input equalization.

TX Input EQ Advertisement
^^^^^^^^^^^^^^^^^^^^^^^^^

.. _cmis_tx_input_eq_ctrl:

.. figure:: ../../images/cmis_tx_input_eq_ctrl.png

    TX Input EQ Control


TX Input EQ Register
^^^^^^^^^^^^^^^^^^^^

For the host to apply new TX SI settings, the ``AdaptiveInputEqEnableTx`` must be cleared as defined in :numref:`cmis_tx_input_eq_ctrl`. This will disable the adaptive EQ and allow the host to apply new TX SI settings.

.. _cmis_tx_input_eq_reg:

.. figure:: ../../images/cmis_tx_input_eq_reg.png

    TX Input EQ Registers

TX Input EQ register control: ``Page 10h, Byte 153 – 159``, as defined in :numref:`cmis_tx_input_eq_reg`, can be used to control the TX input EQ settings.

