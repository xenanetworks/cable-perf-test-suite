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
import logging
from .reportgen import *

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
        self.report_gen = TcvrRxOutputEqTestReportGenerator()
        self.report_gen.chassis = self.tester_obj.info.host
        self.report_filename = report_filename

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
    def module_list(self):
        return self.test_config.module_list
    
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
    
    async def change_module_media(self):
        await change_module_media(self.tester_obj, self.module_list, self.module_media, self.port_speed, self.logger_name,)

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
        # Get logger
        logger = logging.getLogger(self.logger_name)
        logger.info(f"Exhaustive search started")

        # Reserve and reset ports
        logger.info(f"Reserving and reseting ports {self.port_pair_list}")
        tx_port_list: List[FreyaEdunPort] = get_port_obj_list(self.tester_obj, port_pair_list, "tx")
        rx_port_list: List[FreyaEdunPort] = get_port_obj_list(self.tester_obj, port_pair_list, "rx")
        await reserve_reset_ports_in_list(self.tester_obj, tx_port_list)
        await reserve_reset_ports_in_list(self.tester_obj, rx_port_list)
        logger.info(f"Delay after reset: {self.delay_after_reset}s")
        await asyncio.sleep(self.delay_after_reset)

        # check if the transceiver supports RX Output Eq Control
        for rx_port_obj in rx_port_list:
            support_flag = await rx_output_eq_control_supported(rx_port_obj, self.logger_name)
            if not support_flag:
                logger.warning(f"RX Output Eq Control is not supported by Port {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id}")
                return

        # exhaustive search of all cursor combinations
        for tx_port_obj, rx_port_obj in zip(tx_port_list, rx_port_list):
            logger.info(f"-- Port Pair: {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id} -> {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id} --")
            
            # configure prbs
            logger.info(f"Configuring PRBS polynomial to {self.prbs_polynomial.name}")
            polynomial = self.prbs_polynomial
            await tx_port_obj.layer1.prbs_config.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=polynomial, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.ACCUMULATIVE)
            await rx_port_obj.layer1.prbs_config.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=polynomial, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.ACCUMULATIVE)

            # start prbs
            logger.info(f"Starting {self.prbs_polynomial.name} on Port {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id} on Lane {self.lane}")
            _serdes_index = self.lane - 1
            await tx_port_obj.layer1.serdes[_serdes_index].prbs.control.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSON, error_on_off=enums.ErrorOnOff.ERRORSOFF)

            # check if the transceiver module supports Hot Reconfiguration
            result = []
            reconfig_supported = await hot_reconfiguration_supported(rx_port_obj, self.logger_name)
            logger.warning(f"Reconfiguration supported on Port {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id}: {reconfig_supported.name}")
            if reconfig_supported == ReconfigurationSupport.Neither:
                logger.warning(f"Neither Reconfiguration supported on Port {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id}")
                logger.warning(f"RX Output EQ Test aborted!")
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
                                await rx_port_obj.layer1.pcs_fec.clear.set()
                                await tx_port_obj.layer1.pcs_fec.clear.set()

                                # measure duration
                                logger.info(f"Measuring PRBS for {self.prbs_duration}s")
                                await asyncio.sleep(self.prbs_duration)

                                # read PRBS BER
                                prbs_ber = await read_prbs_ber(port=rx_port_obj, lane=self.lane, logger_name=self.logger_name)
                                logger.info(f"Lane ({self.lane}) Amplitude: {amp_value}, PreCursor: {pre_value}, PostCursor: {post_value}, PRBS BER: {prbs_ber}")

                                # save result to report
                                self.report_gen.record_data(port_name=f"Port {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id}", lane=self.lane, amplitude=amp_value, precursor=pre_value, postcursor=post_value, prbs_ber=prbs_ber)

                                # remember the result
                                result.append({"amp": amp_value, "pre": pre_value, "post": post_value, "prbs_ber": prbs_ber})
                            else:
                                logger.info(f"Write operation failed. Skip the PRBS test.")
            
            # Generate report
            logger.info(f"Generatinging test report..")
            self.report_gen.generate_report(self.report_filename)

            # stop prbs
            logger.info(f"Stopping {self.prbs_polynomial.name} on Port {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id} on Lane {self.lane}")
            _serdes_index = self.lane - 1
            await tx_port_obj.layer1.serdes[_serdes_index].prbs.control.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSOFF, error_on_off=enums.ErrorOnOff.ERRORSOFF)

            # find the best
            if len(result) > 0:
                sorted_result = sorted(result, key = lambda x: x["prbs_ber"])
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
        await self.change_module_media()
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
        self.report_gen = TcvrTxInputEqTestReportGenerator()
        self.report_gen.chassis = self.tester_obj.info.host
        self.report_filename = report_filename

        # Get logger
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
        return self.test_config.module_list
    
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
    
    async def change_module_media(self):
        await change_module_media(self.tester_obj, self.module_list, self.module_media, self.port_speed, self.logger_name,)

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
        # Get logger
        logger = logging.getLogger(self.logger_name)
        logger.info(f"Exhaustive search started")

        # Reserve and reset ports
        logger.info(f"Reserving and reseting ports {self.port_pair_list}")
        tx_port_list: List[FreyaEdunPort] = get_port_obj_list(self.tester_obj, port_pair_list, "tx")
        rx_port_list: List[FreyaEdunPort] = get_port_obj_list(self.tester_obj, port_pair_list, "rx")
        await reserve_reset_ports_in_list(self.tester_obj, tx_port_list)
        await reserve_reset_ports_in_list(self.tester_obj, rx_port_list)
        logger.info(f"Delay after reset: {self.delay_after_reset}s")
        await asyncio.sleep(self.delay_after_reset)

        # check if the transceiver supports TX Input EQ Host Control
        for rx_port_obj in rx_port_list:
            support_flag = await tx_input_eq_host_control_supported(rx_port_obj, self.logger_name)
            if not support_flag:
                logger.warning(f"TX Input EQ Host Control is not supported by Port {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id}")
                return

        # exhaustive search of all cursor combinations
        for tx_port_obj, rx_port_obj in zip(tx_port_list, rx_port_list):
            logger.info(f"-- Port Pair: {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id} -> {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id} --")
            
            # configure prbs
            logger.info(f"Configuring PRBS polynomial to {self.prbs_polynomial.name}")
            polynomial = self.prbs_polynomial
            await tx_port_obj.layer1.prbs_config.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=polynomial, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.ACCUMULATIVE)
            await rx_port_obj.layer1.prbs_config.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=polynomial, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.ACCUMULATIVE)

            # start prbs
            logger.info(f"Starting {self.prbs_polynomial.name} on Port {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id} on Lane {self.lane}")
            _serdes_index = self.lane - 1
            await tx_port_obj.layer1.serdes[_serdes_index].prbs.control.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSON, error_on_off=enums.ErrorOnOff.ERRORSOFF)

            # check if the transceiver module supports Hot Reconfiguration
            result = []
            reconfig_supported = await hot_reconfiguration_supported(rx_port_obj, self.logger_name)
            logger.warning(f"Reconfiguration supported on Port {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id}: {reconfig_supported.name}")
            if reconfig_supported == ReconfigurationSupport.Neither:
                logger.warning(f"Neither Reconfiguration supported on Port {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id}")
                logger.warning(f"TX Input EQ Test Aborted!")
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
                        await rx_port_obj.layer1.pcs_fec.clear.set()
                        await tx_port_obj.layer1.pcs_fec.clear.set()

                        # measure duration
                        logger.info(f"Measuring PRBS for {self.prbs_duration}s")
                        await asyncio.sleep(self.prbs_duration)

                        # read PRBS BER
                        prbs_ber = await read_prbs_ber(port=rx_port_obj, lane=self.lane, logger_name=self.logger_name)
                        logger.info(f"Lane ({self.lane}) Equalizer: {eq_value}, PRBS BER: {prbs_ber}")

                        # save result to reporeqst
                        self.report_gen.record_data(port_name=f"Port {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id}", lane=self.lane, eq=eq_value, prbs_ber=prbs_ber)

                        # remember the result
                        result.append({"tx_eq": eq_value, "prbs_ber": prbs_ber})
                    else:
                        logger.info(f"Write operation failed. Skip the PRBS test.")
                
                # Disable Host Controlled EQ
                await disable_host_controlled_eq(tx_port_obj, lane=self.lane, logger_name=self.logger_name)
            
            # Generate report
            logger.info(f"Generating test report...")
            self.report_gen.generate_report(self.report_filename)
            
            # stop prbs
            logger.info(f"Stopping {self.prbs_polynomial.name} on Port {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id} on Lane {self.lane}")
            _serdes_index = self.lane - 1
            await tx_port_obj.layer1.serdes[_serdes_index].prbs.control.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSOFF, error_on_off=enums.ErrorOnOff.ERRORSOFF)

            # find the best
            if len(result) > 0:
                sorted_result = sorted(result, key = lambda x: x["prbs_ber"])
                logger.info(f"Final sorted results:")
                for i in sorted_result:
                    logger.info(f"Lane ({self.lane}) - Tcvr Tx Eq: {i['tx_eq']}, PRBS BER: {i['prbs_ber']}")
                logger.info(f"Best result: Tcvr Tx Eq: {sorted_result[0]['tx_eq']}, PRBS BER: {sorted_result[0]['prbs_ber']}")
                
            else:
                logger.info(f"No results found")
    
    async def run(self):
        self.validate_lane()
        self.validate_transceiver_eq_config()
        await self.change_module_media()
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
        self.report_gen = HostTxEqTestReportGenerator()
        self.report_gen.chassis = self.tester_obj.info.host
        self.report_filename = report_filename

        logger = logging.getLogger(self.logger_name)
        logger.info(f"=============== Host Tx Equalization Optimization Test ===============")
        logger.info(f"Test Config:")
        logger.info(f"  Port Pair:            {self.port_pair_list}")
        logger.info(f"  Lanes:                {self.lanes}")
        logger.info(f"  Delay After Reset:    {self.delay_after_reset} seconds")
        logger.info(f"  Delay After EQ Write: {self.delay_after_eq_write} seconds")
        logger.info(f"  PRBS Polynomial:      {self.prbs_polynomial.name}")
        logger.info(f"  PRBS Duration:        {self.prbs_duration} seconds")
        logger.info(f"  Target BER:           {self.target_ber}")
        logger.info(f"  Preset Tap Values:    {self.preset_tap_values}")
        logger.info(f"  Search Mode:          {self.search_mode}")
        logger.info(f"  Search Taps:          {self.search_taps}")
    
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
        return self.test_config.module_list
    
    @property
    def port_speed(self):
        return self.test_config.port_speed
    
    @property
    def lanes(self):
        return self.test_config.lanes
    
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
    def delay_after_eq_write(self):
        return self.test_config.delay_after_eq_write

    @property
    def prbs_duration(self):
        return self.test_config.prbs_config.duration
    
    @property
    def target_ber(self):
        return self.test_config.target_ber
    
    @property
    def preset_tap_values(self):
        dump = self.test_config.preset_tap_values.model_dump()
        return [dump["pre3"], dump["pre2"], dump["pre1"], dump["main"], dump["post1"], dump["post2"]]
    
    @property
    def search_mode(self):
        return self.test_config.search_mode
    
    @property
    def search_taps(self):
        return self.test_config.search_taps
    
    async def change_module_media(self):
        await change_module_media(self.tester_obj, self.module_list, self.module_media, self.port_speed, self.logger_name,)

    def validate_lanes(self) -> bool:
        # lanes should not have value greater than 8
        if max(self.lanes) > 8 or min(self.lanes) < 1:
            logging.warning(f"Lane must in range[1,8]")
            return False
        return True
    
    async def heuristic_search(self, port_pair_list: List[Dict[str, str]]):
        # Get logger
        logger = logging.getLogger(self.logger_name)
        logger.info(f"Heuristic search started")

        # Reserve and reset ports
        logger.info(f"Reserving and reseting ports {self.port_pair_list}")
        tx_port_obj_list = get_port_obj_list(self.tester_obj, port_pair_list, "tx")
        rx_port_obj_list = get_port_obj_list(self.tester_obj, port_pair_list, "rx")
        await reserve_reset_ports_in_list(self.tester_obj, tx_port_obj_list)
        await reserve_reset_ports_in_list(self.tester_obj, rx_port_obj_list)
        logger.info(f"Delay after reset: {self.delay_after_reset}s")
        await asyncio.sleep(self.delay_after_reset)

        # heuristic search per port pair
        for tx_port_obj, rx_port_obj in zip(tx_port_obj_list, rx_port_obj_list):
            txp = f"Port {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id}"
            rxp = f"Port {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id}"

            cap_struct = await tx_port_obj.capabilities.get()
            num_txeq = cap_struct.tx_eq_tap_count
            num_txeq_pre = cap_struct.num_txeq_pre
            num_txeq_post = num_txeq - num_txeq_pre - 1
            tx_taps_max = cap_struct.txeq_max_seq
            tx_taps_min = cap_struct.txeq_min_seq

            # setup report record structure
            self.report_gen.num_tx_taps = num_txeq
            self.report_gen.num_txtaps_pre = num_txeq_pre
            self.report_gen.num_txtaps_post = num_txeq_post
            self.report_gen.setup_record_structure()

            logger.info(f"-- Port Pair: {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id} -> {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id} --")

            # configure prbs
            logger.info(f"Configuring PRBS polynomial to {self.prbs_polynomial.name}")
            polynomial = self.prbs_polynomial
            await tx_port_obj.layer1.prbs_config.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=polynomial, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.ACCUMULATIVE)
            await rx_port_obj.layer1.prbs_config.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=polynomial, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.ACCUMULATIVE)

            # start prbs on a lane
            await start_prbs_on_lanes(tx_port_obj, self.lanes, self.logger_name)

            # load preset tap values
            await load_preset_tx_tap_values(tx_port_obj, self.lanes, self.preset_tap_values, self.logger_name)

            # Wait for a certain duration to let the EQ settings take effect.
            logger.info(f"Delay after EQ write: {self.delay_after_eq_write}s")
            await asyncio.sleep(self.delay_after_eq_write)

            # clear counters
            logger.info(f"Clearing PRBS counters")
            await rx_port_obj.layer1.pcs_fec.clear.set()
            await tx_port_obj.layer1.pcs_fec.clear.set()

            # measure duration
            logger.info(f"Measuring PRBS for {self.prbs_duration}s")
            await asyncio.sleep(self.prbs_duration)
            
            # read the previous prbs
            prbs_bers = await read_prbs_bers(port=rx_port_obj, lanes=self.lanes, logger_name=self.logger_name)
            last_prbs_bers = prbs_bers

            # save result to report
            tx_tapss=[self.preset_tap_values] * len(self.lanes)
            self.report_gen.record_data(tx_port=txp, rx_port=rxp, lanes=self.lanes, tx_tapss=tx_tapss, prbs_bers=prbs_bers)

            # stop prbs on a lane
            await stop_prbs_on_lanes(tx_port_obj, self.lanes, self.logger_name)

            # heuristic search on host tx eq
            # Increment tap until PRBS BER gets worse
            # pick the prbs that is larger than target ber
            lanes_to_optimize = get_lanes_to_optimize(prbs_bers, self.target_ber)

            for tap_index in self.search_taps:
                logger.info(f"Increment c({tap_index}) on Lanes {lanes_to_optimize}")
                while True:
                    lanes_to_optimize = await change_tx_tap_on_lanes(tx_port_obj, lanes_to_optimize, tap_index, num_txeq_pre, num_txeq_post, tx_taps_max, tx_taps_min, "inc")
                
                    # Wait for a certain duration to let the EQ settings take effect.
                    logger.info(f"Delay after EQ write: {self.delay_after_eq_write}s")
                    await asyncio.sleep(self.delay_after_eq_write)

                    # clear counters
                    logger.info(f"Clearing PRBS counters")
                    await rx_port_obj.layer1.pcs_fec.clear.set()
                    await tx_port_obj.layer1.pcs_fec.clear.set()

                    # start prbs on a lane
                    await start_prbs_on_lanes(tx_port_obj, lanes_to_optimize, self.logger_name)

                    # measure duration
                    logger.info(f"Measuring PRBS for {self.prbs_duration}s")
                    await asyncio.sleep(self.prbs_duration)

                    # read current PRBS BER
                    prbs_bers = await read_prbs_bers(port=rx_port_obj, lanes=lanes_to_optimize, logger_name=self.logger_name)
                    tx_tapss = await read_tx_taps_on_lanes(tx_port_obj, lanes_to_optimize)
                    for lane_index, tx_taps, prbs_ber in zip(lanes_to_optimize, tx_tapss, prbs_bers):
                        logger.info(f"Lane ({lane_index}) Equalizer: {tx_taps}, PRBS BER: {prbs_ber}")

                    # update last prbs bers
                    last_prbs_bers = update_last_prbs_bers_for_opt_lanes(last_prbs_bers, lanes_to_optimize, self.lanes)
                    
                    # save result to report
                    self.report_gen.record_data(tx_port=txp, rx_port=rxp, lanes=lanes_to_optimize, tx_tapss=tx_tapss, prbs_bers=prbs_bers)

                    # stop prbs on a lane
                    await stop_prbs_on_lanes(tx_port_obj, lanes_to_optimize, self.logger_name)

                    # check prbs ber improvement
                    for prbs_ber, last_prbs_ber in zip(prbs_bers, last_prbs_bers):
                        idx = prbs_bers.index(prbs_ber)
                        if prbs_ber <= self.target_ber:
                            logger.info(f"Lane {lanes_to_optimize[idx]}: Target BER {self.target_ber} reached. Stopping optimization.")
                            lanes_to_optimize.remove(lanes_to_optimize[idx])
                        if prbs_ber <= last_prbs_ber:
                            logger.info(f"Lane {lanes_to_optimize[idx]}: PRBS BER improved from {last_prbs_ber} to {prbs_ber}, continue...")
                            last_prbs_bers[idx] = prbs_ber
                            continue
                        else:
                            logger.info(f"Lane {lanes_to_optimize[idx]}: PRBS BER worsened from {last_prbs_ber} to {prbs_ber}, revert last change.")
                            await change_tx_tap_on_lanes(tx_port_obj, [lanes_to_optimize[idx]-1], tap_index, num_txeq_pre, num_txeq_post, tx_taps_max, tx_taps_min, "dec")
                            break
            
            for prbs_ber, last_prbs_ber in zip(prbs_bers, last_prbs_bers):
                idx = prbs_bers.index(prbs_ber)
                if prbs_ber > self.target_ber:
                    logger.info(f"Lane {lanes_to_optimize[idx]}: Could not reach target BER {self.target_ber} with heuristic search.")

            # Generate report
            logger.info(f"Generatinging test report..")
            self.report_gen.generate_report(self.report_filename)

            # stop prbs
            logger.info(f"Stopping {self.prbs_polynomial.name} on Port {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id} on Lane {self.lanes}")
            # stop prbs on a lane
            await stop_prbs_on_lanes(tx_port_obj, self.lanes, self.logger_name)

    async def exhaustive_search(self, port_pair_list: List[Dict[str, str]]):
        # Get logger
        logger = logging.getLogger(self.logger_name)
        logger.info(f"Exhaustive search started")

        # Reserve and reset ports
        logger.info(f"Reserving and reseting ports {self.port_pair_list}")
        tx_port_obj_list = get_port_obj_list(self.tester_obj, port_pair_list, "tx")
        rx_port_obj_list = get_port_obj_list(self.tester_obj, port_pair_list, "rx")
        await reserve_reset_ports_in_list(self.tester_obj, tx_port_obj_list)
        await reserve_reset_ports_in_list(self.tester_obj, rx_port_obj_list)
        logger.info(f"Delay after reset: {self.delay_after_reset}s")
        await asyncio.sleep(self.delay_after_reset)

        # exhaustive search per port pair
        for tx_port_obj, rx_port_obj in zip(tx_port_obj_list, rx_port_obj_list):
            txp = f"Port {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id}"
            rxp = f"Port {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id}"
            
            result_on_lanes = []

            cap_struct = await tx_port_obj.capabilities.get()
            num_txeq = cap_struct.tx_eq_tap_count
            num_txeq_pre = cap_struct.num_txeq_pre
            num_txeq_post = num_txeq - num_txeq_pre - 1
            tx_taps_max = cap_struct.txeq_max_seq
            tx_taps_min = cap_struct.txeq_min_seq

            # setup report record structure
            self.report_gen.num_tx_taps = num_txeq
            self.report_gen.num_txtaps_pre = num_txeq_pre
            self.report_gen.num_txtaps_post = num_txeq_post
            self.report_gen.setup_record_structure()

            logger.info(f"-- Port Pair: {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id} -> {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id} --")

            # configure prbs
            logger.info(f"Configuring PRBS polynomial to {self.prbs_polynomial.name}")
            polynomial = self.prbs_polynomial
            await tx_port_obj.layer1.prbs_config.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=polynomial, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.ACCUMULATIVE)
            await rx_port_obj.layer1.prbs_config.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=polynomial, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.ACCUMULATIVE)

            # heuristic search on host tx eq
            # Increment tap until PRBS BER gets worse
            
            for _tap_index in self.search_taps:
                # load preset tap values
                await load_preset_tx_tap_values(tx_port_obj, self.lanes, self.preset_tap_values, self.logger_name)

                # Wait for a certain duration to let the EQ settings take effect.
                logger.info(f"Delay after EQ write: {self.delay_after_eq_write}s")
                await asyncio.sleep(self.delay_after_eq_write)

                # clear counters
                logger.info(f"Clearing PRBS counters")
                await rx_port_obj.layer1.pcs_fec.clear.set()
                await tx_port_obj.layer1.pcs_fec.clear.set()

                # start prbs on a lane
                await start_prbs_on_lanes(tx_port_obj, self.lanes, self.logger_name)

                # measure duration
                logger.info(f"Measuring PRBS for {self.prbs_duration}s")
                await asyncio.sleep(self.prbs_duration)
                
                # read the previous prbs
                prbs_bers = await read_prbs_bers(port=rx_port_obj, lanes=self.lanes, logger_name=self.logger_name)

                # save result to 
                tx_tapss=[self.preset_tap_values] * len(self.lanes)
                self.report_gen.record_data(tx_port=txp, rx_port=rxp, lanes=self.lanes, tx_tapss=tx_tapss, prbs_bers=prbs_bers)
                for lane_index, tx_taps, prbs_ber in zip(self.lanes, tx_tapss, prbs_bers):
                    result_on_lanes.append({"lane": lane_index,"tx_eq": tx_taps, "prbs_ber": prbs_ber})

                # stop prbs on a lane
                await stop_prbs_on_lanes(tx_port_obj, self.lanes, self.logger_name)

                logger.info(f"Increment c({_tap_index})")
                keep_optimizing = True
                while keep_optimizing:
                    lanes_to_optimize = []
                    lanes_to_optimize = await change_tx_tap_on_lanes(tx_port_obj, self.lanes, _tap_index, num_txeq_pre, num_txeq_post, 
                    tx_taps_max, tx_taps_min, "inc")

                    if len(lanes_to_optimize) == 0:
                        logger.info(f"All lanes reached maximum value for tap c({_tap_index})")
                        keep_optimizing = False
                        continue
                    
                    # Wait for a certain duration to let the EQ settings take effect.
                    logger.info(f"Delay after EQ write: {self.delay_after_eq_write}s")
                    await asyncio.sleep(self.delay_after_eq_write)

                    # clear counters
                    logger.info(f"Clearing PRBS counters")
                    await rx_port_obj.layer1.pcs_fec.clear.set()
                    await tx_port_obj.layer1.pcs_fec.clear.set()

                    # start prbs on a lane
                    await start_prbs_on_lanes(tx_port_obj, lanes_to_optimize, self.logger_name)

                    # measure duration
                    logger.info(f"Measuring PRBS for {self.prbs_duration}s")
                    await asyncio.sleep(self.prbs_duration)

                    # read current PRBS BER
                    prbs_bers = await read_prbs_bers(port=rx_port_obj, lanes=lanes_to_optimize, logger_name=self.logger_name)
                    tx_tapss = await read_tx_taps_on_lanes(tx_port_obj, lanes=lanes_to_optimize)
                    for lane_index, tx_taps, prbs_ber in zip(lanes_to_optimize, tx_tapss, prbs_bers):
                        logger.info(f"Lane ({lane_index}) Equalizer: {tx_taps}, PRBS BER: {prbs_ber}")

                    # save result to report
                    self.report_gen.record_data(tx_port=txp, rx_port=rxp, lanes=lanes_to_optimize, tx_tapss=tx_tapss, prbs_bers=prbs_bers)
                    for lane_index, tx_taps, prbs_ber in zip(lanes_to_optimize, tx_tapss, prbs_bers):
                        result_on_lanes.append({"lane": lane_index,"tx_eq": tx_taps, "prbs_ber": prbs_ber})

                    # stop prbs on a lane
                    await stop_prbs_on_lanes(tx_port_obj, lanes_to_optimize, self.logger_name)
            
            # Generate report
            logger.info(f"Generatinging test report..")
            self.report_gen.generate_report(self.report_filename)

            # stop prbs
            await stop_prbs_on_lanes(tx_port_obj, self.lanes, self.logger_name)

            # find the best per lane
            logger.info(f"Final sorted results:")
            for lane in self.lanes:
                lane_results = [res for res in result_on_lanes if res["lane"] == lane]
                if len(lane_results) > 0:
                    sorted_result = sorted(lane_results, key = lambda x: x["prbs_ber"])
                    for i in sorted_result:
                        logger.info(f"Lane ({lane}) - Host Tx Eq: {i['tx_eq']}, PRBS BER: {i['prbs_ber']}")
                    logger.info(f"Best result: Host Tx Eq: {sorted_result[0]['tx_eq']}, PRBS BER: {sorted_result[0]['prbs_ber']}")
                    logger.info(f"Writing the best result to Host Tx Eq")
                    await tx_port_obj.layer1.serdes[lane-1].medium.tx.native.set(tap_values=sorted_result[0]['tx_eq'])
                else:
                    logger.info(f"Lane ({lane}): No result found")


        # except asyncio.CancelledError:
        #     logging.error(f"Statistics collection cancelled.")
        # finally:
        #     # # Generate report
        #     # logger.info(f"Generatinging test report..")
        #     # self.report_gen.generate_report(self.report_filename)

        #     # # stop prbs
        #     # for tx_port_obj in tx_port_obj_list:
        #     #     await stop_prbs_on_lanes(tx_port_obj, self.lanes, self.logger_name)
        #     pass

            

            
    
    async def run(self):
        self.validate_lanes()
        # await self.change_module_media()
        if self.search_mode == "heuristic":
            await self.heuristic_search(self.port_pair_list)
        elif self.search_mode == "exhaustive":
            await self.exhaustive_search(self.port_pair_list)    
        else:
            logger = logging.getLogger(self.logger_name)
            logger.error(f"Invalid search mode: {self.search_mode}. Supported modes are 'heuristic' and 'exhaustive'.") 
    
