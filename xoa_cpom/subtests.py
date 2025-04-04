# *************************************
# author: leonard.yu@teledyne.com
# *************************************

import asyncio
from xoa_driver import testers, modules, ports, enums
from xoa_driver.hlfuncs import mgmt
from xoa_cpom.utils import *
from xoa_cpom.cmisfuncs import *
from .models import *
import logging

# *************************************************************************************
# class: XenaRxOutputEqOptimization
# description: This class provides an automated optimization framework that uses 
# PRBS-based BER testing to dial in RX Output Equalization afor the best 
# possible signal integrity.
# *************************************************************************************
class XenaRxOutputEqOptimization:
    """
    This class provides an automated optimization framework that uses PRBS-based BER testing to dial in RX Output Equalization afor the best possible signal integrity.
    """
    def __init__(self, tester_obj: testers.L23Tester, test_config: RXOutputEqTestConfig, logger_name: str):
        self.tester_obj = tester_obj
        self.test_config = test_config
        self.logger_name = logger_name

        # Get logger
        logger = logging.getLogger(self.logger_name)
        logger.info(f"## RxOutputEqOptimalTest ##")
        logger.info(f"Port Pair:            {self.port_pair_list}")
        logger.info(f"Lane:                 {self.lane}")
        logger.info(f"Amplitude Range:      [{self.amp_min}, {self.amp_max}]")
        logger.info(f"PreCursor Range:      [{self.pre_min}, {self.pre_max}]")
        logger.info(f"PostCursor Range:     [{self.post_min}, {self.post_max}]")
        logger.info(f"Delay After Reset:    {self.delay_after_reset} seconds")
        logger.info(f"Delay After EQ Write: {self.delay_after_eq_write} seconds")
        logger.info(f"PRBS Duration:        {self.prbs_duration} seconds")
    
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

        # Reserve and reset ports
        logger.info(f"Reserve and reset ports")
        tx_port_list: List[ports.Z800FreyaPort] = get_port_list(self.tester_obj, port_pair_list, "tx")
        rx_port_list: List[ports.Z800FreyaPort] = get_port_list(self.tester_obj, port_pair_list, "rx")
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
            logger.info(f"Start exhaustive search of RX Output EQ")
            
            # configure prbs
            logger.info(f"Configure PRBS polynomial: {self.prbs_polynomial}")
            polynomial = self.prbs_polynomial
            await tx_port_obj.pcs_pma.prbs_config.type.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=polynomial, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.ACCUMULATIVE)
            await rx_port_obj.pcs_pma.prbs_config.type.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=polynomial, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.ACCUMULATIVE)

            # start prbs
            logger.info(f"Start PRBS on Port {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id} on Lane {self.lane}")
            _serdes_index = self.lane - 1
            await tx_port_obj.l1.serdes[_serdes_index].prbs.control.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSON, error_on_off=enums.ErrorOnOff.ERRORSOFF)

            # check if the transceiver module supports Hot Reconfiguration
            result = []
            hotreconfig_supported = await hot_reconfiguration_supported(rx_port_obj, self.logger_name)
            if not hotreconfig_supported:
                logger.warning(f"Hot Reconfiguration is not supported on Port {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id}")
            else:
                for amp_value in range(self.amp_min, self.amp_max+1):
                    for pre_value in range(self.pre_min, self.pre_max+1):
                        for post_value in range(self.post_min, self.post_max+1):

                            logger.info(f"Amplitude: {amp_value}, PreCursor: {pre_value}, PostCursor: {post_value}")

                            # Write the RX output EQ settings to the RX Output EQ registers.
                            await rx_output_eq_write(port=rx_port_obj, lane=self.lane, value=amp_value, cursor=Cursor.Amplitude, logger_name=self.logger_name)
                            await rx_output_eq_write(port=rx_port_obj, lane=self.lane, value=pre_value, cursor=Cursor.Precursor, logger_name=self.logger_name)
                            await rx_output_eq_write(port=rx_port_obj, lane=self.lane, value=post_value, cursor=Cursor.Postcursor, logger_name=self.logger_name)
                            
                            # Trigger the Provision-and-Commission procedure
                            await trigger_provision_and_commission(port=rx_port_obj, lane=self.lane, logger_name=self.logger_name)

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
                                logger.info(f"Clear PRBS counters")
                                await rx_port_obj.pcs_pma.rx.clear.set()
                                await tx_port_obj.pcs_pma.rx.clear.set()

                                # measure duration
                                logger.info(f"PRBS measure for {self.prbs_duration}s")
                                await asyncio.sleep(self.prbs_duration)

                                # read PRBS BER
                                prbs_ber = await read_prbs_ber(port=rx_port_obj, lane=self.lane, logger_name=self.logger_name)
                                logger.info(f"Lane ({self.lane}) - Amplitude: {amp_value}, PreCursor: {pre_value}, PostCursor: {post_value}, PRBS BER: {prbs_ber}")

                                # remember the result
                                result.append({"amp": amp_value, "pre": pre_value, "post": post_value, "prbs_ber": prbs_ber})
                            else:
                                logger.info(f"Write operation failed. Skip the PRBS test.")
            
            # stop prbs
            logger.info(f"Stop PRBS on Port {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id} on Lane {self.lane}")
            _serdes_index = self.lane - 1
            await tx_port_obj.l1.serdes[_serdes_index].prbs.control.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSOFF, error_on_off=enums.ErrorOnOff.ERRORSOFF)

            # find the best
            if len(result) > 0:
                sorted_result = sorted(result, key = lambda x: x["prbs_ber"])
                logger.info(f"Final sorted results:")
                for i in sorted_result:
                    logger.info(f"Lane ({self.lane}) - Amplitude: {i['amp']}, PreCursor: {i['pre']}, PostCursor: {i['post']}, PRBS BER: {i['prbs_ber']}")
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
# PRBS-based BER testing to dial in TX Input Equalization afor the best 
# possible signal integrity.
# *************************************************************************************
class XenaTxInputEqOptimization:
    """
    This class provides an automated optimization framework that uses PRBS-based BER testing to dial in TX Input Equalization afor the best possible signal integrity.
    """
    def __init__(self, tester_obj: testers.L23Tester, test_config: TxInputEqTestConfig, logger_name: str):
        self.tester_obj = tester_obj
        self.test_config = test_config
        self.logger_name = logger_name

        # Get logger
        logger = logging.getLogger(self.logger_name)
        logger.info(f"## TxInputEqOptimalTest ##")
        logger.info(f"Port Pair:            {self.port_pair_list}")
        logger.info(f"Lane:                 {self.lane}")
        logger.info(f"TX EQ Range:          [{self.eq_min}, {self.eq_max}]")
        logger.info(f"Delay After Reset:    {self.delay_after_reset} seconds")
        logger.info(f"Delay After EQ Write: {self.delay_after_eq_write} seconds")
        logger.info(f"PRBS Duration:        {self.prbs_duration} seconds")
    
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

        # Reserve and reset ports
        logger.info(f"Reserve and reset ports")
        tx_port_list: List[ports.Z800FreyaPort] = get_port_list(self.tester_obj, port_pair_list, "tx")
        rx_port_list: List[ports.Z800FreyaPort] = get_port_list(self.tester_obj, port_pair_list, "rx")
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
            logger.info(f"Start exhaustive search of TX Input EQ")
            
            # configure prbs
            logger.info(f"Configure PRBS polynomial: {self.prbs_polynomial}")
            polynomial = self.prbs_polynomial
            await tx_port_obj.pcs_pma.prbs_config.type.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=polynomial, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.ACCUMULATIVE)
            await rx_port_obj.pcs_pma.prbs_config.type.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=polynomial, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.ACCUMULATIVE)

            # start prbs
            logger.info(f"Start PRBS on Port {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id} on Lane {self.lane}")
            _serdes_index = self.lane - 1
            await tx_port_obj.l1.serdes[_serdes_index].prbs.control.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSON, error_on_off=enums.ErrorOnOff.ERRORSOFF)

            # check if the transceiver module supports Hot Reconfiguration
            result = []
            hotreconfig_supported = await hot_reconfiguration_supported(rx_port_obj, self.logger_name)
            if not hotreconfig_supported:
                logger.warning(f"Hot Reconfiguration is not supported on Port {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id}")
            else:
                # Enable Host Controlled EQ
                await enable_host_controlled_eq(tx_port_obj, lane=self.lane, logger_name=self.logger_name)

                for eq_value in range(self.eq_min, self.eq_max+1):

                    logger.info(f"TX Input EQ: {eq_value}")

                    # Write the TX input EQ setting to the TX Input EQ registers.
                    await tx_input_eq_write(port=rx_port_obj, lane=self.lane, value=eq_value, logger_name=self.logger_name)
                    
                    # Trigger the Provision-and-Commission procedure
                    await trigger_provision_and_commission(port=rx_port_obj, lane=self.lane, logger_name=self.logger_name)

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
                        logger.info(f"Clear PRBS counters")
                        await rx_port_obj.pcs_pma.rx.clear.set()
                        await tx_port_obj.pcs_pma.rx.clear.set()

                        # measure duration
                        logger.info(f"PRBS measure for {self.prbs_duration}s")
                        await asyncio.sleep(self.prbs_duration)

                        # read PRBS BER
                        prbs_ber = await read_prbs_ber(port=rx_port_obj, lane=self.lane, logger_name=self.logger_name)
                        logger.info(f"Lane ({self.lane}) - TX Input EQ {eq_value}, PRBS BER: {prbs_ber}")

                        # remember the result
                        result.append({"tx_eq": eq_value, "prbs_ber": prbs_ber})
                    else:
                        logger.info(f"Write operation failed. Skip the PRBS test.")
                
                # Disable Host Controlled EQ
                await disable_host_controlled_eq(tx_port_obj, lane=self.lane, logger_name=self.logger_name)
            
            # stop prbs
            logger.info(f"Stop PRBS on Port {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id} on Lane {self.lane}")
            _serdes_index = self.lane - 1
            await tx_port_obj.l1.serdes[_serdes_index].prbs.control.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSOFF, error_on_off=enums.ErrorOnOff.ERRORSOFF)

            # find the best
            if len(result) > 0:
                sorted_result = sorted(result, key = lambda x: x["prbs_ber"])
                logger.info(f"Final sorted results:")
                for i in sorted_result:
                    logger.info(f"Lane ({self.lane}) - TX EQ: {i['tx_eq']}, PRBS BER: {i['prbs_ber']}")
            else:
                logger.info(f"No results found")
    
    async def run(self):
        self.validate_lane()
        self.validate_transceiver_eq_config()
        await self.change_module_media()
        await self.exhaustive_search(self.port_pair_list)        
    

