# *************************************
# author: leonard.yu@teledyne.com
# *************************************

import asyncio
from xoa_driver import testers, modules, ports, enums
from xoa_driver.hlfuncs import mgmt
from xoa_cpom.utils import *
from xoa_cpom.cmisfuncs import *
from .models import *
from .enums import *
from .reportgen import *
from .prbs_control import *
from .txeq_control import *

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
    def __init__(self, tester_obj: testers.L23Tester, test_config: TcvrRxOutputEqTestConfig, logger_name: str, report_filename: str):
        self.tester_obj = tester_obj
        self.test_config = test_config
        self.logger_name = logger_name
        self.report_filename = report_filename
        self.report_gen = TcvrRxOutputEqTestReportGenerator(
            logger_name=self.logger_name, 
            name="Tcvr Rx Output EQ Test", 
            chassis=self.tester_obj.info.host)
        
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
    def module_list(self) -> List[int]:
        results = set()
        for port_pair in self.test_config.port_pair_list:
            results.add(int(port_pair.tx.split("/")[0]))
        return list(results)
    
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
        for module_id in self.module_list:
            module_str_configs.append((str(module_id), self.test_config.module_media, self.test_config.port_speed))

        await config_modules(self.tester_obj, module_str_configs, self.logger_name)

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
        port_pair_obj_list = portid_to_portobj(self.tester_obj, port_pair_list)            

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
    def __init__(self, tester_obj: testers.L23Tester, test_config: TcvrTxInputEqTestConfig, logger_name: str, report_filename: str):
        self.tester_obj = tester_obj
        self.test_config = test_config
        self.logger_name = logger_name
        self.report_filename = report_filename
        self.report_gen = TcvrTxInputEqTestReportGenerator(
            logger_name=self.logger_name, 
            name="Tcvr Rx Output EQ Test", 
            chassis=self.tester_obj.info.host)
        
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
    def module_list(self):
        results = set()
        for port_pair in self.test_config.port_pair_list:
            results.add(int(port_pair.tx.split("/")[0]))
        return list(results)
    
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
        for module_id in self.module_list:
            module_str_configs.append((str(module_id), self.test_config.module_media, self.test_config.port_speed))

        await config_modules(self.tester_obj, module_str_configs, self.logger_name)

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
        port_pair_obj_list = portid_to_portobj(self.tester_obj, port_pair_list) 

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
    


# *************************************************************************************
# class: XenaHostTxEqOptimization
# description: This class provides an automated optimization framework that uses 
# PRBS-based BER testing to test Host Tx Equalization for the best 
# possible signal integrity.
# *************************************************************************************
class XenaHostTxEqOptimization:
    """
    This class provides an automated optimization framework that uses PRBS-based BER testing to test Host Tx Equalization for the best possible signal integrity.
    """
    def __init__(self, tester_obj: testers.L23Tester, test_config: HostTxEqTestConfig, logger_name: str, report_filename: str):
        self.tester_obj = tester_obj
        self.test_config = test_config
        self.logger_name = logger_name
        self.report_filename = report_filename
        self.report_gen = HostTxEqTestReportGenerator(
            logger_name=self.logger_name, 
            name="Host Tx EQ Test", 
            chassis=self.tester_obj.info.host)        

        logger = logging.getLogger(self.logger_name)
        logger.info(f"=============== Host Tx Equalization Optimization Test ===============")
        logger.info(f"Test Config")
        logger.info(f"  Port Pair:            {self.port_pair_list}")
        logger.info(f"  Lanes:                {self.lanes}")
        logger.info(f"  Delay After Reset:    {self.delay_after_reset} seconds")
        logger.info(f"  Delay After EQ Write: {self.delay_after_eq_write} seconds")
        logger.info(f"  PRBS Polynomial:      {self.prbs_polynomial.name}")
        logger.info(f"  PRBS Duration:        {self.prbs_duration} seconds")
        logger.info(f"  Target BER:           {self.target_ber}")
        logger.info(f"  Start Tx Eq Values:   {self.start_txeq_values}")
        logger.info(f"  Optimize Mode:        {self.optimize_mode}")
        logger.info(f"  Optimize Tx Eq Ids:   {self.optimize_txeq_ids}")
    
    @property
    def port_pair_list(self):
        port_pair_dicts = []
        for port_pair in self.test_config.port_pair_list:
            port_pair_dicts.append(port_pair.model_dump())
        return port_pair_dicts
    
    @property
    def module_media(self):
        return enums.MediaConfigurationType[self.test_config.module_media]
    
    @property
    def module_list(self) -> List[int]:
        results = set()
        for port_pair in self.test_config.port_pair_list:
            results.add(int(port_pair.tx.split("/")[0]))
        return list(results)
    
    @property
    def port_speed(self) -> str:
        return self.test_config.port_speed
    
    @property
    def lanes(self) -> List[int]:
        return self.test_config.lanes
    
    @property
    def delay_after_reset(self) -> int:
        return self.test_config.delay_after_reset
    
    @property
    def prbs_config(self):
        return self.test_config.prbs_config.model_dump()

    @property
    def prbs_polynomial(self) -> enums.PRBSPolynomial:
        return enums.PRBSPolynomial[self.test_config.prbs_config.polynomial]

    @property
    def delay_after_eq_write(self) -> int:
        return self.test_config.delay_after_eq_write

    @property
    def prbs_duration(self) -> int:
        return self.test_config.prbs_config.duration
    
    @property
    def target_ber(self) -> float:
        return self.test_config.target_ber
    
    @property
    def start_txeq_values(self) -> List[int]:
        dump = self.test_config.start_txeq.model_dump()
        return [dump["pre3"], dump["pre2"], dump["pre1"], dump["main"], dump["post1"], dump["post2"]]
    
    @property
    def optimize_mode(self) -> str:
        return self.test_config.optimize_mode
    
    @property
    def optimize_txeq_ids(self) -> List[int]:
        return self.test_config.optimize_txeq_ids
    
    async def config_modules(self):
        module_str_configs = []
        for module_id in self.module_list:
            module_str_configs.append((str(module_id), self.test_config.module_media, self.test_config.port_speed))

        await config_modules(self.tester_obj, module_str_configs, self.logger_name)

    def validate_lanes(self) -> bool:
        # lanes should not have value greater than 8
        if max(self.lanes) > 8 or min(self.lanes) < 1:
            logging.warning(f"Lane must in range[1,8]")
            return False
        return True
    
    async def heuristic_search(self, port_pair_list: List[Dict[str, str]]):
        logger = logging.getLogger(self.logger_name)
        logger.info(f"Heuristic search started")

        # Get port pair objects list from port pair list
        port_pair_obj_list = portid_to_portobj(self.tester_obj, port_pair_list)  

        # heuristic search per port pair
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

            port_txeq_limits = await get_port_txeq_limits(tx_port_obj)

            # setup report record structure
            self.report_gen.setup(
                num_tx_taps=port_txeq_limits.num_txeq,
                num_txtaps_pre=port_txeq_limits.num_txeq_pre,
                num_txtaps_post=port_txeq_limits.num_txeq_post
            )

            # configure prbs
            await config_prbs([tx_port_obj, rx_port_obj], self.prbs_polynomial, self.logger_name)

            # load preset tap values
            logger.info(f"Writing starting Tx Eq values")
            await write_txeq_to_lanes(tx_port_obj, [(lane, self.start_txeq_values) for lane in self.lanes], self.delay_after_eq_write, self.logger_name)

            # clear counters
            await clear_prbs_counters(rx_port_obj, self.logger_name)

            # run prbs on lanes
            await run_prbs_on_lanes(tx_port_obj, self.lanes, self.prbs_duration, self.logger_name)
            
            # read current PRBS BER and current TxEqs
            lane_ber_dicts = await read_ber_from_lanes(port=rx_port_obj, lanes=self.lanes, logger_name=self.logger_name)
            txeq_dicts = await read_txeq_from_lanes(tx_port_obj, lanes=self.lanes)

            # save reading to report
            self.report_gen.record_data(port_name=f"{tx_port_txt} -> {rx_port_txt}", lane_ber_dicts=lane_ber_dicts, lane_txeqs_dicts=txeq_dicts)

            # remove lanes and their ber reading that already meet target ber
            lane_ber_dicts = get_below_target_lane_ber_dicts(lane_ber_dicts, self.target_ber, self.logger_name)
            lanes_to_optimize = [item["lane"] for item in lane_ber_dicts]
            best_lane_ber_dicts = copy.deepcopy(lane_ber_dicts)
            
            for txeq_id in self.optimize_txeq_ids:
                while len(lanes_to_optimize) > 0:
                    logger.info(f"## Optimizing c({txeq_id}) on Lanes {lanes_to_optimize} ##")
                    # adjust txeq on lanes, and update lanes to optimize
                    lanes_to_optimize = await optimize_txeq_on_lanes(tx_port_obj, lanes_to_optimize, txeq_id, "inc", self.delay_after_eq_write, self.logger_name, port_txeq_limits)
                    if len(lanes_to_optimize) == 0:
                        logger.info(f"No lane to optimize. Quit optimization.")
                        break
                
                    # clear counters
                    await clear_prbs_counters(rx_port_obj, self.logger_name)

                    # run prbs on lanes
                    await run_prbs_on_lanes(tx_port_obj, lanes_to_optimize, self.prbs_duration, self.logger_name)

                    # read current PRBS BER and current TxEqs
                    lane_ber_dicts = await read_ber_from_lanes(port=rx_port_obj, lanes=lanes_to_optimize, logger_name=self.logger_name)
                    txeq_dicts = await read_txeq_from_lanes(tx_port_obj, lanes=lanes_to_optimize)
                    
                    # save result to report
                    self.report_gen.record_data(port_name=f"{tx_port_txt} -> {rx_port_txt}", lane_ber_dicts=lane_ber_dicts, lane_txeqs_dicts=txeq_dicts)

                    # determine lanes to continue optimization
                    lane_ber_dicts = get_below_target_lane_ber_dicts(lane_ber_dicts, self.target_ber, self.logger_name)
                    lane_ber_dicts = update_lane_ber_dicts(lane_ber_dicts, best_lane_ber_dicts, self.logger_name)
                    lanes_to_optimize = [item["lane"] for item in lane_ber_dicts]
                    if len(lanes_to_optimize) == 0:
                        logger.info(f"No lane to optimize. Quit optimization.")
                        break
                    worsen_lane_ber_dict = get_worsen_lane_ber_dicts(lane_ber_dicts, best_lane_ber_dicts, self.logger_name)
                    best_lane_ber_dicts = update_best_lane_ber_dicts(lane_ber_dicts, best_lane_ber_dicts)
                    await optimize_txeq_on_lanes(tx_port_obj, [int(item["lane"]) for item in worsen_lane_ber_dict], txeq_id, "dec", self.delay_after_eq_write, self.logger_name, port_txeq_limits)
                
            # check if any lane did not meet target ber
            await clear_prbs_counters(rx_port_obj, self.logger_name)
            await run_prbs_on_lanes(tx_port_obj, self.lanes, self.prbs_duration, self.logger_name)
            lane_ber_dicts = await read_ber_from_lanes(port=rx_port_obj, lanes=self.lanes, logger_name=self.logger_name)
            lane_ber_dicts = get_below_target_lane_ber_dicts(lane_ber_dicts, self.target_ber, self.logger_name)
            for lane_ber_dict in lane_ber_dicts:
                logger.warning(f"Lane ({lane_ber_dict['lane']}) did not meet target BER {self.target_ber}. Final BER: {lane_ber_dict['prbs_ber']}")
            
            # Generate report
            logger.info(f"Generatinging test report..")
            self.report_gen.generate_report(self.report_filename)

    async def exhaustive_search(self, port_pair_list: List[Dict[str, str]]):
        logger = logging.getLogger(self.logger_name)
        logger.info(f"Exhaustive search started")

        # Get port pair objects list from port pair list
        port_pair_obj_list = portid_to_portobj(self.tester_obj, port_pair_list)  

        # heuristic search per port pair
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
            
            result_on_lanes = []
            port_txeq_limits = await get_port_txeq_limits(tx_port_obj)

            # setup report record structure
            self.report_gen.setup(
                num_tx_taps=port_txeq_limits.num_txeq,
                num_txtaps_pre=port_txeq_limits.num_txeq_pre,
                num_txtaps_post=port_txeq_limits.num_txeq_post
            )

            # configure prbs
            await config_prbs([tx_port_obj, rx_port_obj], self.prbs_polynomial, self.logger_name)

            # load preset tap values
            logger.info(f"Writing starting Tx Eq values")
            await write_txeq_to_lanes(tx_port_obj, [(lane, self.start_txeq_values) for lane in self.lanes], self.delay_after_eq_write, self.logger_name)

            # clear counters
            await clear_prbs_counters(rx_port_obj, self.logger_name)

            # run prbs on lanes
            await run_prbs_on_lanes(tx_port_obj, self.lanes, self.prbs_duration, self.logger_name)
            
            # read current PRBS BER and current TxEqs
            lane_ber_dicts = await read_ber_from_lanes(port=rx_port_obj, lanes=self.lanes, logger_name=self.logger_name)
            txeq_dicts = await read_txeq_from_lanes(tx_port_obj, lanes=self.lanes)

            # save reading to report
            self.report_gen.record_data(port_name=f"{tx_port_txt} -> {rx_port_txt}", lane_ber_dicts=lane_ber_dicts, lane_txeqs_dicts=txeq_dicts)

            sorted_lane_ber_dicts = sorted(lane_ber_dicts, key=lambda x: x["lane"])
            sorted_txeq_dicts = sorted(txeq_dicts, key=lambda x: x["lane"])
            for lane_ber_dict, txeq_dict in zip(sorted_lane_ber_dicts, sorted_txeq_dicts):
                result_on_lanes.append({"lane": lane_ber_dict["lane"], "tx_eq": txeq_dict["txeq_values"], "prbs_ber": lane_ber_dict["prbs_ber"]})

            for txeq_id in self.optimize_txeq_ids:
                logger.info(f"Optimize c({txeq_id}) on Lanes {self.lanes}")
                keep_optimizing = True
                while keep_optimizing:
                    lanes_to_optimize = []
                    lanes_to_optimize = await optimize_txeq_on_lanes(tx_port_obj, self.lanes, txeq_id, "inc", self.delay_after_eq_write, self.logger_name, port_txeq_limits)

                    if len(lanes_to_optimize) == 0:
                        logger.info(f"No lane to optimize for c({txeq_id})")
                        keep_optimizing = False
                        continue

                    # clear counters
                    await clear_prbs_counters(rx_port_obj, self.logger_name)

                    # run prbs on lanes
                    await run_prbs_on_lanes(tx_port_obj, self.lanes, self.prbs_duration, self.logger_name)

                    # read current PRBS BER and current TxEqs
                    lane_ber_dicts = await read_ber_from_lanes(port=rx_port_obj, lanes=self.lanes, logger_name=self.logger_name)
                    txeq_dicts = await read_txeq_from_lanes(tx_port_obj, lanes=self.lanes)

                    # save result to report
                    self.report_gen.record_data(port_name=f"{tx_port_txt} -> {rx_port_txt}", lane_ber_dicts=lane_ber_dicts, lane_txeqs_dicts=txeq_dicts)
                    sorted_lane_ber_dicts = sorted(lane_ber_dicts, key=lambda x: x["lane"])
                    sorted_txeq_dicts = sorted(txeq_dicts, key=lambda x: x["lane"])
                    for lane_ber_dict, txeq_dict in zip(sorted_lane_ber_dicts, sorted_txeq_dicts):
                        result_on_lanes.append({"lane": lane_ber_dict["lane"], "tx_eq": txeq_dict["txeq_values"], "prbs_ber": lane_ber_dict["prbs_ber"]})

                # write the best tap values to lanes as the starting point for next iteration
                lane_txeq_list = []
                for lane in self.lanes:
                    lane_results = [res for res in result_on_lanes if res["lane"] == lane]
                    if len(lane_results) > 0:
                        sorted_result = sorted(lane_results, key = lambda x: x["prbs_ber"])
                        for i in sorted_result:
                            logger.info(f"Lane ({lane}) - Host Tx Eq: {i['tx_eq']}, PRBS BER: {i['prbs_ber']}")
                        logger.info(f"Best result: Host Tx Eq: {sorted_result[0]['tx_eq']}, PRBS BER: {sorted_result[0]['prbs_ber']}")
                        logger.info(f"Writing the current best result to Host Tx Eq as starting point for next iteration")
                        lane_txeq_list.append((lane, sorted_result[0]['tx_eq']))
                    else:
                        logger.info(f"Lane ({lane}): No result found")
                await write_txeq_to_lanes(tx_port_obj, lane_txeq_list, self.delay_after_eq_write, self.logger_name)
            
            # Generate report
            logger.info(f"Generatinging test report..")
            self.report_gen.generate_report(self.report_filename)

            # write the final best result to lanes
            logger.info(f"[Final Result]")
            lane_txeq_list = []
            for lane in self.lanes:
                lane_results = [res for res in result_on_lanes if res["lane"] == lane]
                if len(lane_results) > 0:
                    sorted_result = sorted(lane_results, key = lambda x: x["prbs_ber"])
                    for i in sorted_result:
                        logger.info(f"Lane ({lane}) - Host Tx Eq: {i['tx_eq']}, PRBS BER: {i['prbs_ber']}")
                    logger.info(f"Best result: Host Tx Eq: {sorted_result[0]['tx_eq']}, PRBS BER: {sorted_result[0]['prbs_ber']}")
                    logger.info(f"Writing the best result to Host Tx Eq as final result")
                    lane_txeq_list.append((lane, sorted_result[0]['tx_eq']))
                else:
                    logger.info(f"Lane ({lane}): No result found")
            await write_txeq_to_lanes(tx_port_obj, lane_txeq_list, self.delay_after_eq_write, self.logger_name)
            
    
    async def run(self):
        self.validate_lanes()
        await self.config_modules()
        if self.optimize_mode == "heuristic":
            await self.heuristic_search(self.port_pair_list)
        elif self.optimize_mode == "exhaustive":
            await self.exhaustive_search(self.port_pair_list)    
        else:
            logger = logging.getLogger(self.logger_name)
            logger.error(f"Invalid search mode: {self.optimize_mode}. Supported modes are 'heuristic' and 'exhaustive'.") 
    
