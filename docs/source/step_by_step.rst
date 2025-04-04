Step-by-Step
=============================

Prerequisite
-------------

1. Download the latest release `Cable Performance Optimization Methodology Releases <https://github.com/xenanetworks/cable-perf-test-suite/releases>`_
2. Install the required Python packages by running the following command:

.. code-block:: bash

      pip install -r requirements.txt

The required packages are listed in the ``requirements.txt`` file.

.. note::

    ``tdl-xoa-driver`` is developed by Teledyne LeCroy Xena. You can read more about this package in `XOA Driver Documentation <https://docs.xenanetworks.com/projects/tdl-xoa-driver/en/latest/index.html>`_.

Change Test Configuration
-------------------------

Go to ``test/`` directory, change the ``test_config.yml`` to meet your test setup and requirements.

.. code-block:: yaml

    test_config:
      chassis_ip: "10.165.136.60"
      username: "CPOM"
      password: "xena"
      tcp_port: 22606
      log_filename: "xena_cpom.log"
      rx_output_eq_test_config:
        module_list:
          - 3
          - 6
        port_pair_list:
          - tx: "3/0"
            rx: "6/0"
        module_media: "QSFPDD800"
        port_speed: "1x800G"
        lane: 1
        delay_after_reset: 2
        prbs_config:
          polynomial: "PRBS31"
          duration: 2
        rx_output_eq_range:
          amp_min: 0
          amp_max: 3
          pre_min: 0
          pre_max: 7
          post_min: 0
          post_max: 7
        delay_after_eq_write: 2
      tx_input_eq_test_config:
        module_list:
          - 3
          - 6
        port_pair_list:
          - tx: "3/0"
            rx: "6/0"
        module_media: "QSFPDD800"
        port_speed: "1x800G"
        lane: 1
        delay_after_reset: 2
        prbs_config:
          polynomial: "PRBS31"
          duration: 2
        tx_input_eq_range:
          min: 0
          max: 12
        delay_after_eq_write: 2

* ``chassis_ip``: the IP address of the chassis
* ``username``: the name used to connect to the chassis and reserve ports
* ``password``: the password used to connect to the chassis
* ``tcp_port``: the port number used to connect to the chassis
* ``log_filename``: the log filename
* ``rx_output_eq_test_config``: the test configuration of RX output equalization optimization

    * ``module_list``: a list of module IDs to test  
    * ``port_pair_list``: a list of port pairs

        * ``tx``: the ID (module/port) of the port that transmits PRBS
        * ``rx``: the ID (module/port) of the port that measures PRBS BER

    * ``module_media``: the module media mode to apply
    * ``port_speed``: the port speed mode in the format of <port count>x<port speed>
    * ``lane``: the lane index you want to test, from 1 to 8.
    * ``delay_after_reset``: waiting time in seconds after port reset
    * ``prbs_config``

        * ``polynomial``: the PRBS polynomial to use
        * ``duration``: PRBS BER measurement duration in seconds

    * ``rx_output_eq_range``:

        * ``amp_min``: the minimum amplitude cursor code value
        * ``amp_max``: the maximum amplitude cursor code value
        * ``pre_min``: the minimum pre-cursor code value
        * ``pre_max``: the maximum pre-cursor code value
        * ``post_min``: the minimum post-cursor code value
        * ``post_max``: the maximum post-cursor code value
    
    * ``delay_after_eq_write``: waiting time in seconds after writing the cursor values

* ``tx_input_eq_test_config``: the test configuration of TX input equalization optimization
  
    * ``module_list``: a list of module IDs to test
    * ``port_pair_list``: a list of port pairs

        * ``tx``: the ID (module/port) of the port that transmits PRBS
        * ``rx``: the ID (module/port) of the port that measures PRBS BER

    * ``module_media``: the module media mode to apply
    * ``port_speed``: the port speed mode in the format of <port count>x<port speed>
    * ``lane``: the lane index you want to test, from 1 to 8.
    * ``delay_after_reset``: waiting time in seconds after port reset
    * ``prbs_config``

        * ``polynomial``: the PRBS polynomial to use
        * ``duration``: PRBS BER measurement duration in seconds

    * ``tx_input_eq_range``:

        * ``min``: the minimum code value
        * ``max``: the maximum code value
    
    * ``delay_after_eq_write``: waiting time in seconds after writing the cursor values

Run the Test
------------

Then, run ``python test.py`` to start the test. The test log and results will be saved in the log file specified in the test configuration and also printed on the console.

.. figure:: images/test_in_process.png

    Test in process

.. figure:: images/test_result.png

    Test results