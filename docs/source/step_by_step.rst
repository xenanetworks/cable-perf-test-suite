Step-by-Step
=============================

Prerequisite
-------------

1. Install tdl-xoa-driver. Read `install tdl-xoa-driver <https://docs.xenanetworks.com/projects/tdl-xoa-driver/en/latest/getting_started/index.html>`_ for details.
2. Download the library and the test example together with the test configuraiton from `Cable Performance Optimization Methodology GitHub Repository <https://github.com/xenanetworks/cable-perf-test-suite/>`_


Change Test Configuration
-------------------------

Go to ``test/`` directory, change the ``test_config.yml`` to meet your test setup and requirements.

.. code-block:: yaml

    test_config:
      chassis_ip: "10.165.153.101"
      username: "CablePerformanceTest"
      password: "xena"
      tcp_port: 22606
      log_filename: "cable_perf_test.log"
      rx_output_eq_test_config:
        port_pair_list:
          - tx: "0/0"
            rx: "0/1"
        module_media: "OSFPDD800_ANLT"
        port_speed: "2x400G"
        lane: 1
        delay_after_reset: 2
        prbs_test_config:
          polynomial: "PRBS31"
          duration: 2
        transceiver_eq_config:
          amp_min: 0
          amp_max: 7
          pre_min: 0
          pre_max: 7
          post_min: 0
          post_max: 7
          delay_after_eq_write: 2

* chassis_ip: the IP address of the chassis
* username: the name used to connect to the chassis and reserve ports
* password: the password used to connect to the chassis
* tcp_port: the port number used to connect to the chassis
* log_filename: the log filename
* rx_output_eq_test_config: the test configuration of RX output equalization ptimization

    * port_pair_list: a list of port pairs

        * tx: the ID (module/port) of the port that transmits PRBS
        * rx: the ID (module/port) of the port that measures PRBS BER

    * module_media: the module media mode to apply
    * port_speed: the port speed mode in the format of <port count>x<port speed>
    * lane: the lane index you want to test, from 1 to 8.
    * delay_after_reset: waiting time in seconds after port reset
    * prbs_test_config

        * polynomial: the PRBS polynomial to use
        * duration: PRBS BER measurement duration in seconds

    * transceiver_eq_config:

        * amp_min: the minimum amplitude cursor code value
        * amp_max: the maximum amplitude cursor code value
        * pre_min: the minimum pre-cursor code value
        * pre_max: the maximum pre-cursor code value
        * post_min: the minimum post-cursor code value
        * post_max: the maximum post-cursor code value
        * delay_after_eq_write: waiting time in seconds after writing the cursor values


Run the Test
------------

Then, run ``python test.py`` to start the test. The test log and results will be saved in the log file specified in the test configuration and also printed on the console.

.. figure:: images/test_in_process.png

    Test in process

.. figure:: images/test_result.png

    Test results