# *************************************
# author: leonard.yu@teledyne.com
# *************************************

import asyncio
from xoa_driver import testers, modules, ports, enums
from xoa_driver.hlfuncs import mgmt
from xoa_cpom.utils import *
from xoa_cpom.cmisfuncs import *
from ..models import *
from ..enums import *
from ..reportgen import *
from ..prbs_control import *
from ..txeq_control import *
from typing import List, Dict, Set

import logging
import copy

# *************************************************************************************
# class: XenaTxInputEqOptimization
# description: This class provides an automated optimization framework that uses 
# PRBS-based BER testing to test Tcvr Tx Input Equalization for the best 
# possible signal integrity.
# *************************************************************************************
class XenaTcvrTxInputEqOptimization:
    """
    This class provides an automated optimization framework that uses PRBS-based BER testing to test Module Tx Input Equalization for the best possible signal integrity.
    """
    def __init__(self, tester_objs: List[testers.L23Tester], test_config: TcvrTxInputEqTestConfig, logger_name: str, report_filename: str):
        self.tester_objs = tester_objs
        self.test_config = test_config
        self.logger_name = logger_name
        self.report_filename = report_filename
        self.report_gen = TcvrTxInputEqTestReportGenerator(
            logger_name=self.logger_name, 
            name="Tcvr Rx Output EQ Test", 
            chassis_list=[tester.info.host for tester in self.tester_objs])
        
        logger = logging.getLogger(self.logger_name)
        logger.info(f"=============== Tcvr Tx Input Equalization Optimization Test ===============")
        logger.info(f"Test Config:")
        logger.info(f"  Port Pair:            {self.port_pair_list}")
        logger.info(f"  Lane:                 {self.lane}")
        logger.info(f"  TX EQ Range:          [{self.eq_min}, {self.eq_max}]")
        logger.info(f"  Delay After Reset:    {self.delay_after_reset} seconds")
        logger.info(f"  Delay After EQ Write: {self.delay_after_eq_write} seconds")
        logger.info(f"  PRBS Polynomial:      {self.prbs_polynomial.name}")
        logger.info(f"  PRBS Duration:        {self.prbs_duration} seconds")

    @property
    def port_pair_list(self):
        __list = []
        for port_pair in self.test_config.port_pair_list:
            __list.append(port_pair.model_dump())
        return __list
    
    @property
    def module_media(self):
        return enums.MediaConfigurationType[self.test_config.module_media]
    
    @property
    def chassis_modules_dict(self) -> Dict[str, Set[int]]:
        result = dict()
        # - tx: "10.165.136.77:0/1"
        #   rx: "10.165.136.70:0/1"
        for port_pair in self.test_config.port_pair_list:
            chassis_ip = port_pair.tx.split(":")[0]
            module_id = port_pair.tx.split(":")[1].split("/")[0]
            if chassis_ip not in result.keys():
                result[chassis_ip] = set()
            result[chassis_ip].add(int(module_id))
            chassis_ip = port_pair.rx.split(":")[0]
            module_id = port_pair.rx.split(":")[1].split("/")[0]
            if chassis_ip not in result.keys():
                result[chassis_ip] = set()
            result[chassis_ip].add(int(module_id))
        return result
    
    @property
    def port_speed(self):
        return self.test_config.port_speed
    
    @property
    def lane(self):
        return self.test_config.lane
    
    @property
    def delay_after_reset(self):
        return self.test_config.delay_after_reset
    
    @property
    def prbs_config(self):
        return self.test_config.prbs_config.model_dump()

    @property
    def prbs_polynomial(self) -> enums.PRBSPolynomial:
        return enums.PRBSPolynomial[self.test_config.prbs_config.polynomial]

    @property
    def eq_min(self):
        return self.test_config.tx_input_eq_range.min
    
    @property
    def eq_max(self):
        return self.test_config.tx_input_eq_range.max
    
    @property
    def delay_after_eq_write(self):
        return self.test_config.delay_after_eq_write

    @property
    def prbs_duration(self):
        return self.test_config.prbs_config.duration
    
    async def config_modules(self):
        module_str_configs = []
        for chassis_ip, module_ids in self.chassis_modules_dict.items():
            module_str_configs.append((str(module_ids), self.test_config.module_media, self.test_config.port_speed))
            tester_obj = find_tester_obj(chassis_ip, self.tester_objs)
            await config_modules(tester_obj, module_str_configs, self.logger_name)

    def validate_lane(self) -> bool:
        if not 1<=self.lane<=8:
            logging.warning(f"Lane must in range[1,8]")
            return False
        return True

    def validate_transceiver_eq_config(self) -> bool:
        if self.eq_min > self.eq_max:
            logging.warning(f"EQ range error! You entered EQ Min ({self.eq_min}) > EQ Max ({self.eq_max}).")
            return False
        if self.eq_max > 15:
            logging.warning(f"EQ Max > 15 error! eq_max: {self.eq_max}")
            return False
        if self.eq_min <0:
            logging.warning(f"EQ Min < 0 error! eq_min: {self.eq_min}")
            return False
        return True
    
    async def exhaustive_search(self, port_pair_list: List[dict]):
        logger = logging.getLogger(self.logger_name)
        logger.info(f"Exhaustive search started")

        # Get port pair objects list from port pair list
        port_pair_obj_list = await convert_port_ids_to_objects(self.tester_objs, port_pair_list) 

        # exhaustive search of all cursor combinations
        for port_pair_obj in port_pair_obj_list:
            tx_port_obj: FreyaEdunPort = port_pair_obj["tx"] # type: ignore
            rx_port_obj: FreyaEdunPort = port_pair_obj["rx"] # type: ignore
            tx_port_txt = f"Port {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id}"
            rx_port_txt = f"Port {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id}"

            logger.info(f"-- Port Pair: {tx_port_txt} -> {rx_port_txt} --")
            logger.info(f"Reserving and reseting port pair")
            await mgmt.reserve_ports(ports=[tx_port_obj, rx_port_obj], reset=True)
            logger.info(f"Delay after reset: {self.delay_after_reset}s")
            await asyncio.sleep(self.delay_after_reset)

            # check if the transceiver supports TX Input EQ Host Control
            if not await tx_input_eq_host_control_supported(rx_port_obj, self.logger_name):
                logger.warning(f"TX Input EQ Host Control is not supported by {rx_port_txt}")
                return
            
            # configure prbs
            await config_prbs([tx_port_obj, rx_port_obj], self.prbs_polynomial, self.logger_name)

            results_to_sort = []
            # check if the module supports Reconfiguration
            reconfig_supported = await check_eq_reconfig_support(rx_port_obj, self.logger_name)
            
            if reconfig_supported == ReconfigurationSupport.Neither:
                logger.warning(f"Neither Reconfiguration supported on {rx_port_txt}")
                logger.warning(f"TX Input EQ Test Aborted!")
                return
            else:
                _appsel_code, _dp_id, _explicit_ctrl = await dp_read(port=rx_port_obj, lane=self.lane, logger_name=self.logger_name)
                await dp_write(port=rx_port_obj, lane=self.lane, appsel_code=_appsel_code, dp_id=_dp_id, explicit_ctrl=1, logger_name=self.logger_name)

                # Enable Host Controlled EQ
                await enable_host_controlled_eq(tx_port_obj, lane=self.lane, logger_name=self.logger_name)

                for eq_value in range(self.eq_min, self.eq_max+1):

                    logger.info(f"Equalizer: {eq_value}")

                    # Write the TX input EQ setting to the TX Input EQ registers.
                    await tx_input_eq_write(port=tx_port_obj, lane=self.lane, value=eq_value, logger_name=self.logger_name)
                    
                    # Trigger the Provision-and-Commission procedure
                    await apply_change_on_lane(port=tx_port_obj, lane=self.lane, logger_name=self.logger_name, reconfig_support=reconfig_supported)

                    # Read ConfigStatus register to check if the EQ settings are applied.
                    while True:
                        config_status = await read_config_status(port=tx_port_obj, lane=self.lane, logger_name=self.logger_name)
                        if config_status == ConfigStatus.ConfigInProgress:
                            logger.info(f"  ConfigStatus is still ConfigInProgress. Please wait for the configuration to complete.")
                            await asyncio.sleep(1)
                            continue
                        elif config_status == ConfigStatus.ConfigSuccess:
                            logger.info(f"  Write operation successful")
                            break
                        else:
                            logger.info(f"  Write operation failed. (ConfigStatus is {config_status.name})")
                            break
                    
                    if config_status == ConfigStatus.ConfigSuccess:
                        # Wait for a certain duration to let the EQ settings take effect.
                        logger.info(f"Delay after EQ write: {self.delay_after_eq_write}s")
                        await asyncio.sleep(self.delay_after_eq_write)

                        # clear counters
                        logger.info(f"Clearing PRBS counters")
                        await clear_prbs_counters(port=rx_port_obj, logger_name=self.logger_name)

                        # run PRBS for a certain duration
                        await run_prbs_on_lanes(port=tx_port_obj, lanes=[self.lane], duration=self.prbs_duration, logger_name=self.logger_name)

                        # read PRBS BER
                        prbs_bers =await read_ber_from_lanes(port=rx_port_obj, lanes=[self.lane], logger_name=self.logger_name)
                        prbs_ber = prbs_bers[0]["prbs_ber"]

                        # save result to reporeqst
                        self.report_gen.record_data(port_name=f"{tx_port_txt} --> {rx_port_txt}", lane=self.lane, eq_value=eq_value, prbs_ber=prbs_ber)

                        # remember the result
                        results_to_sort.append({"tx_eq": eq_value, "prbs_ber": prbs_ber})
                    else:
                        logger.info(f"Write operation failed. Skip the PRBS test.")
                
                # Disable Host Controlled EQ
                await disable_host_controlled_eq(tx_port_obj, lane=self.lane, logger_name=self.logger_name)
            
                # Generate report
                logger.info(f"Generating test report...")
                self.report_gen.generate_report(self.report_filename)

                # find the best
                if len(results_to_sort) > 0:
                    sorted_result = sorted(results_to_sort, key = lambda x: x["prbs_ber"])
                    logger.info(f"Final sorted results:")
                    for i in sorted_result:
                        logger.info(f"Lane ({self.lane}) - Tcvr Tx Eq: {i['tx_eq']}, PRBS BER: {i['prbs_ber']}")
                    logger.info(f"Best result: Tcvr Tx Eq: {sorted_result[0]['tx_eq']}, PRBS BER: {sorted_result[0]['prbs_ber']}")
                    
                else:
                    logger.info(f"No results found")
    
    async def run(self):
        self.validate_lane()
        self.validate_transceiver_eq_config()
        await self.config_modules()
        await self.exhaustive_search(self.port_pair_list)        
    