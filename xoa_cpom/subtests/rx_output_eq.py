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
# class: XenaRxOutputEqOptimization
# description: This class provides an automated optimization framework that uses 
# PRBS-based BER testing to test Tcvr Rx Output Equalization for the best 
# possible signal integrity.
# *************************************************************************************
class XenaTcvrRxOutputEqOptimization:
    """
    This class provides an automated optimization framework that uses PRBS-based BER testing to test Module Rx Output Equalization for the best possible signal integrity.
    """
    def __init__(self, tester_objs: List[testers.L23Tester], test_config: TcvrRxOutputEqTestConfig, logger_name: str, report_filename: str):
        self.tester_objs = tester_objs
        self.test_config = test_config
        self.logger_name = logger_name
        self.report_filename = report_filename
        self.report_gen = TcvrRxOutputEqTestReportGenerator(
            logger_name=self.logger_name, 
            name="Tcvr Rx Output EQ Test", 
            chassis_list=[tester.info.host for tester in self.tester_objs])
        
        logger = logging.getLogger(self.logger_name)
        logger.info(f"=============== Tcvr Rx Output Equalization Optimization Test ===============")
        logger.info(f"Test Config:")
        logger.info(f"  Port Pair:            {self.port_pair_list}")
        logger.info(f"  Lane:                 {self.lane}")
        logger.info(f"  Amplitude Range:      [{self.amp_min}, {self.amp_max}]")
        logger.info(f"  PreCursor Range:      [{self.pre_min}, {self.pre_max}]")
        logger.info(f"  PostCursor Range:     [{self.post_min}, {self.post_max}]")
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
    def amp_min(self):
        return self.test_config.rx_output_eq_range.amp_min
    
    @property
    def amp_max(self):
        return self.test_config.rx_output_eq_range.amp_max
    
    @property
    def pre_min(self):
        return self.test_config.rx_output_eq_range.pre_min
    
    @property
    def pre_max(self):
        return self.test_config.rx_output_eq_range.pre_max
    
    @property
    def post_min(self):
        return self.test_config.rx_output_eq_range.post_min

    @property
    def post_max(self):
        return self.test_config.rx_output_eq_range.post_max
    
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
        if self.amp_min > self.amp_max:
            logging.warning(f"Amplitude range error! You entered min ({self.amp_min}) > max ({self.amp_max}).")
            return False
        if self.pre_min > self.pre_max:
            logging.warning(f"PreCursor range error! You entered min ({self.pre_min}) > max ({self.pre_max}).")
            return False
        if self.post_min > self.post_max:
            logging.warning(f"PostCursor range error! You entered min ({self.post_min}) > max ({self.post_max}).")
            return False
        if self.amp_max > 7 or self.pre_max > 7 or self.post_max > 7:
            logging.warning(f"Max > 7 error! amp_max: {self.amp_max}, pre_max: {self.pre_max}, post_max: {self.post_max}")
            return False
        if self.amp_min < 0 or self.pre_min < 0 or self.post_min < 0:
            logging.warning(f"Min < 0 error! amp_min: {self.amp_min}, pre_min: {self.pre_min}, post_min: {self.post_min}")
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
            
            # check if the transceiver supports RX Output EQ Host Control
            if not await rx_output_eq_control_supported(rx_port_obj, self.logger_name):
                logger.warning(f"RX Output Eq Control is not supported by {rx_port_txt}")
                return

            # configure prbs
            await config_prbs([tx_port_obj, rx_port_obj], self.prbs_polynomial, self.logger_name)
            
            results_to_sort = []
            # check if the module supports Reconfiguration
            reconfig_supported = await check_eq_reconfig_support(rx_port_obj, self.logger_name)
            
            if reconfig_supported == ReconfigurationSupport.Neither:
                logger.warning(f"Neither Reconfiguration supported on {rx_port_txt}")
                logger.warning(f"RX Output EQ Test aborted!")
                return
            else:
                _appsel_code, _dp_id, _explicit_ctrl = await dp_read(port=rx_port_obj, lane=self.lane, logger_name=self.logger_name)
                await dp_write(port=rx_port_obj, lane=self.lane, appsel_code=_appsel_code, dp_id=_dp_id, explicit_ctrl=1, logger_name=self.logger_name)
                for amp_value in range(self.amp_min, self.amp_max+1):
                    for pre_value in range(self.pre_min, self.pre_max+1):
                        for post_value in range(self.post_min, self.post_max+1):
                            logger.info(f"Amplitude: {amp_value}, PreCursor: {pre_value}, PostCursor: {post_value}")
                            # Write the RX output EQ settings to the RX Output EQ registers.
                            await rx_output_eq_write(port=rx_port_obj, lane=self.lane, value=amp_value, cursor=Cursor.Amplitude, logger_name=self.logger_name)
                            await rx_output_eq_write(port=rx_port_obj, lane=self.lane, value=pre_value, cursor=Cursor.Precursor, logger_name=self.logger_name)
                            await rx_output_eq_write(port=rx_port_obj, lane=self.lane, value=post_value, cursor=Cursor.Postcursor, logger_name=self.logger_name)
                            
                            # Trigger the Provision-and-Commission procedure
                            await apply_change_on_lane(port=rx_port_obj, lane=self.lane, logger_name=self.logger_name, reconfig_support=reconfig_supported)

                            # Read ConfigStatus register to check if the EQ settings are applied.
                            while True:
                                config_status = await read_config_status(port=rx_port_obj, lane=self.lane, logger_name=self.logger_name)
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

                                # save result to report
                                self.report_gen.record_data(port_name=f"{tx_port_txt} --> {rx_port_txt}", lane=self.lane, amplitude=amp_value, precursor=pre_value, postcursor=post_value, prbs_ber=prbs_ber)

                                # remember the result
                                results_to_sort.append({"amp": amp_value, "pre": pre_value, "post": post_value, "prbs_ber": prbs_ber})
                            else:
                                logger.info(f"Write operation failed. Skip the PRBS test.")
            
                # Generate report
                logger.info(f"Generatinging test report..")
                self.report_gen.generate_report(self.report_filename)

                # find the best
                if len(results_to_sort) > 0:
                    sorted_result = sorted(results_to_sort, key = lambda x: x["prbs_ber"])
                    logger.info(f"Final sorted results:")
                    for i in sorted_result:
                        logger.info(f"Lane ({self.lane}) - Amplitude: {i['amp']}, PreCursor: {i['pre']}, PostCursor: {i['post']}, PRBS BER: {i['prbs_ber']}")
                    
                    logger.info(f"Best result: Amplitude: {sorted_result[0]['amp']}, PreCursor: {sorted_result[0]['pre']}, PostCursor: {sorted_result[0]['post']}, PRBS BER: {sorted_result[0]['prbs_ber']}")
                    logger.info(f"Writing the best result to Rx Output Eq registers")
                    await rx_output_eq_write(port=rx_port_obj, lane=self.lane, value=sorted_result[0]['amp'], cursor=Cursor.Amplitude, logger_name=self.logger_name)
                    await rx_output_eq_write(port=rx_port_obj, lane=self.lane, value=sorted_result[0]['pre'], cursor=Cursor.Precursor, logger_name=self.logger_name)
                    await rx_output_eq_write(port=rx_port_obj, lane=self.lane, value=sorted_result[0]['post'], cursor=Cursor.Postcursor, logger_name=self.logger_name)
                    await apply_change_on_lane(port=rx_port_obj, lane=self.lane, logger_name=self.logger_name, reconfig_support=reconfig_supported)
                else:
                    logger.info(f"No results found")
    
    async def run(self):
        self.validate_lane()
        self.validate_transceiver_eq_config()
        await self.config_modules()
        await self.exhaustive_search(self.port_pair_list)        
    