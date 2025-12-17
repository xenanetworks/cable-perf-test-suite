# *************************************
# author: leonard.yu@teledyne.com
# *************************************

from xoa_driver import testers, modules, ports, enums
from xoa_driver.hlfuncs import mgmt
from .utils import *
from .models import *
from .subtests import *
import yaml, json
from pathlib import Path
import logging
from typing import Optional

# *************************************************************************************
# class: XenaCablePerfOptimization
# description: This class provides an automated optimization framework that uses 
# PRBS-based BER testing to dial in RX Output Equalization and TX Input Equalization 
# for the best possible signal integrity, aligning with IEEE 802.3ck and CMIS standards.
# *************************************************************************************

class XenaCablePerfOptimization:
    """
    This class provides an automated optimization framework that uses PRBS-based BER testing to dial in RX Output Equalization and TX Input Equalization for the best possible signal integrity, aligning with IEEE 802.3ck and CMIS standards.
    """
    def __init__(self, test_config_file: str, enable_comm_trace: bool = False):
        self.enable_comm_trace = enable_comm_trace
        self.test_config_file = test_config_file
        self.test_config: CablePerformanceTestConfig
        self.tester_obj: testers.L23Tester
        self.rx_output_eq_optimization_test: Optional[XenaTcvrRxOutputEqOptimization] = None
        """
        Optimizing RX Output Equalization        
        """

        self.tx_input_eq_optimization_test: Optional[XenaTcvrTxInputEqOptimization] = None
        """
        Optimizing TX Input Equalization
        """

        self.host_tx_eq_optimization_test: Optional[XenaHostTxEqOptimization] = None
        """
        Optimizing Host TX Equalization
        """

        self.load_test_config(test_config_file)

    async def connect(self):
        """Connect to the chassis and create a tester object, and create a report directory for the test report and logs.
        """
        self.tester_obj = await testers.L23Tester(
            host=self.chassis_ip, 
            username=self.username, 
            password=self.password, 
            port=self.tcp_port, 
            enable_logging=self.enable_comm_trace)

        self.path = await create_report_dir()

        # configure basic logger
        logging.basicConfig(
            format="%(asctime)s  %(message)s",
            level=logging.DEBUG,
            handlers=[
                logging.FileHandler(filename=os.path.join(self.path, self.log_filename), mode="a"),
                logging.StreamHandler()]
            )
        
        logger = logging.getLogger(self.logger_name)
        logger.info(f"#####################################################################")
        logger.info(f"Welcome to Xena Cable Performance Optimization Test")
        logger.info(f"Chassis:              {self.chassis_ip}")
        logger.info(f"Username:             {self.username}")
        logger.info(f"#####################################################################")

    async def disconnect(self):
        """Disconnect from the tester.
        """
        await self.tester_obj.session.logoff()
        logger = logging.getLogger(self.logger_name)
        logger.info(f"Gracefully disconnect from tester")
        logger.info(f"Bye!")

    def load_test_config(self, test_config_file: str):
        """Load the test configuration from a YAML file, and validate it using the CablePerformanceTestConfig model.

        :param test_config_file: test configuration file path
        :type test_config_file: str
        """
        with open(test_config_file, "r") as f:
            test_config_dict = yaml.safe_load(f)
            test_config_value = json.dumps(test_config_dict["test_config"])
            self.test_config = CablePerformanceTestConfig.model_validate_json(test_config_value)

    
    async def run_tx_input_eq_optimization_test(self):
        """Run the TX Input Equalization optimization test, if configured.
        """
        if self.test_config.tcvr_tx_input_eq_test_config is not None:
            self.tx_input_eq_optimization_test = XenaTcvrTxInputEqOptimization(self.tester_obj, self.test_config.tcvr_tx_input_eq_test_config, self.logger_name, self.report_filepathname)
            await self.tx_input_eq_optimization_test.run()

    async def run_rx_output_eq_optimization_test(self):
        """Run the RX Output Equalization optimization test, if configured.
        """
        if self.test_config.tcvr_rx_output_eq_test_config is not None:
            self.rx_output_eq_optimization_test  = XenaTcvrRxOutputEqOptimization(self.tester_obj, self.test_config.tcvr_rx_output_eq_test_config, self.logger_name, self.report_filepathname)
            await self.rx_output_eq_optimization_test.run()

    async def run_host_tx_eq_optimization_test(self):
        """Run the Host TX Equalization optimization test, if configured.
        """
        if self.test_config.host_tx_eq_test_config is not None:
            self.host_tx_eq_optimization_test = XenaHostTxEqOptimization(self.tester_obj, self.test_config.host_tx_eq_test_config, self.logger_name, self.report_filepathname)
            await self.host_tx_eq_optimization_test.run()

    @property
    def chassis_ip(self):
        return self.test_config.chassis_ip
    
    @property
    def username(self):
        return self.test_config.username
    
    @property
    def password(self):
        if self.test_config.password is None:
            return "xena"
        else:
            return self.test_config.password
    
    @property
    def tcp_port(self):
        if self.test_config.tcp_port is None:
            return 22606
        else:
            return self.test_config.tcp_port
    
    @property
    def log_filename(self):
        if self.test_config.log_filename is None:
            return "xena_cpom.log"
        else:
            return self.test_config.log_filename

    @property
    def logger_name(self):
        if self.test_config.log_filename is None:
            return "xena_cpom"
        else:
            return self.log_filename.replace(".log", "")
    
    @property
    def report_filepathname(self):
        return os.path.join(self.path, self.test_config.csv_report_filename)
    
    async def run(self):
        """Run the XenaCablePerfOptimization test.
        """
        await self.connect()
        await self.run_rx_output_eq_optimization_test()
        await self.run_tx_input_eq_optimization_test()
        await self.run_host_tx_eq_optimization_test()
        await self.disconnect()




