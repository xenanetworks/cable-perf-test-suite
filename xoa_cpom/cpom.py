# *************************************
# author: leonard.yu@teledyne.com
# *************************************

from xoa_driver import testers, modules, ports, enums
from xoa_driver.hlfuncs import mgmt
from .utils import *
from .models import *
from .subtests import XenaRxOutputEqOptimization
import yaml, json
from pathlib import Path
import logging

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
        self.rx_output_eq_optimization_test: XenaRxOutputEqOptimization
        """
        Optimizing RX Output Equalization
    
        * What It Does: Controls how the transceiver drives the signal back to the host, adjusting amplitude and emphasis to compensate for losses.
        * Why It Matters: If RX Output Equalization is off, the host’s receiver might struggle to recover the data cleanly, leading to errors.
        
        How We Optimize It:
        
        * Sweep pre-cursor, main-cursor, and post-cursor values to find the best setting.
        * Use BER feedback from PRBS testing to fine-tune the equalizer.
        * Ensure settings comply with CMIS-defined control registers.
        
        """

        script_dir = Path(__file__).resolve().parent
        file_path = script_dir / test_config_file
        self.load_test_config(str(file_path))

    def load_test_config(self, test_config_file: str):
        with open(test_config_file, "r") as f:
            test_config_dict = yaml.safe_load(f)
            test_config_value = json.dumps(test_config_dict["test_config"])
            self.test_config = CablePerformanceTestConfig.model_validate_json(test_config_value)

            # configure basic logger
            logging.basicConfig(
                format="%(asctime)s  %(message)s",
                level=logging.DEBUG,
                handlers=[
                    logging.FileHandler(filename=self.log_filename, mode="a"),
                    logging.StreamHandler()]
                )

    @property
    def chassis_ip(self):
        return self.test_config.chassis_ip
    
    @property
    def username(self):
        return self.test_config.username
    
    @property
    def password(self):
        return self.test_config.password
    
    @property
    def tcp_port(self):
        return self.test_config.tcp_port
    
    @property
    def log_filename(self):
        return self.test_config.log_filename

    @property
    def logger_name(self):
        return self.log_filename.replace(".log", "")
    
    async def connect(self):
        self.tester_obj = await testers.L23Tester(host=self.chassis_ip, username=self.username, password=self.password, port=self.tcp_port, enable_logging=self.enable_comm_trace)

        # Get logger
        logger = logging.getLogger(self.logger_name)
        logger.info(f"#####################################################################")
        logger.info(f"Chassis:              {self.chassis_ip}")
        logger.info(f"Username:             {self.username}")
        logger.info(f"#####################################################################")

        self.rx_output_eq_optimization_test = XenaRxOutputEqOptimization(self.tester_obj, self.test_config.rx_output_eq_test_config, self.logger_name)

    async def disconnect(self):
        await self.tester_obj.session.logoff()



