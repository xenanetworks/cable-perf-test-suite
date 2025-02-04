################################################################
#
#                   OPTIMAL CABLE PERFORMANCE
# 
# This script uses exhaustive search to measure the PRBS BER on 
# each transceiver cursor value combination. At the end, all 
# results are sorted based on PRBS BER value with the best one 
# on the top.
#
# 
################################################################

import asyncio
import sys

from xoa_driver import testers, modules, ports, enums
from xoa_driver.hlfuncs import mgmt
from libs import *
from models import *
import yaml, json
from pathlib import Path
import logging


#-----------------------------
# class CablePerfOptimalTest
#-----------------------------

class CablePerfOptimalTest:
    def __init__(self, test_config_file: str, enable_comm_trace: bool = False):
        self.enable_comm_trace = enable_comm_trace
        self.test_config_file = test_config_file
        self.test_config: CablePerfOptimalTestConfig
        self.tester_obj: testers.L23Tester

        script_dir = Path(__file__).resolve().parent
        file_path = script_dir / test_config_file
        self.load_test_config(str(file_path))

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
    
    @property
    def prbs_test_config(self):
        return self.test_config.prbs_test_config.model_dump()
    
    @property
    def prbs_polynomial(self) -> enums.PRBSPolynomial:
        return enums.PRBSPolynomial[self.test_config.prbs_test_config.polynomial]
    
    @property
    def amp_min(self):
        return self.test_config.transceiver_eq_config.amp_min
    
    @property
    def amp_max(self):
        return self.test_config.transceiver_eq_config.amp_max
    
    @property
    def pre_min(self):
        return self.test_config.transceiver_eq_config.pre_min
    
    @property
    def pre_max(self):
        return self.test_config.transceiver_eq_config.pre_max
    
    @property
    def post_min(self):
        return self.test_config.transceiver_eq_config.post_min
    
    @property
    def post_max(self):
        return self.test_config.transceiver_eq_config.post_max
    
    @property
    def delay_after_reset(self):
        return self.test_config.delay_after_reset
    
    @property
    def lane(self):
        return self.test_config.lane
    
    @property
    def delay_after_eq_write(self):
        return self.test_config.transceiver_eq_config.delay_after_eq_write
    
    @property
    def prbs_duration(self):
        return self.test_config.prbs_test_config.duration
    
    @property
    def port_pair_list(self):
        __list = []
        for port_pair in self.test_config.port_pair_list:
            __list.append(port_pair.model_dump())
        return __list
    
    def load_test_config(self, test_config_file: str):
        with open(test_config_file, "r") as f:
            test_config_dict = yaml.safe_load(f)
            test_config_value = json.dumps(test_config_dict["cable_optimal_test_config"])
            self.test_config = CablePerfOptimalTestConfig.model_validate_json(test_config_value)

            # configure basic logger
            logging.basicConfig(
                format="%(asctime)s  %(message)s",
                level=logging.DEBUG,
                handlers=[
                    logging.FileHandler(filename=self.log_filename, mode="a"),
                    logging.StreamHandler()]
                )
            
    def validate_lane(self) -> bool:
        if not 1<=self.lane<=8:
            logging.warning(f"Lane must in range[1,8]")
            return False
        return True

    def validate_transceiver_eq_config(self, transceiver_eq_config: TransceiverEQConfig) -> bool:
        if transceiver_eq_config.amp_min > transceiver_eq_config.amp_max:
            logging.warning(f"Amplitude range error! You entered min ({transceiver_eq_config.amp_min}) > max ({transceiver_eq_config.amp_max}).")
            return False
        if transceiver_eq_config.pre_min > transceiver_eq_config.pre_max:
            logging.warning(f"PreCursor range error! You entered min ({transceiver_eq_config.pre_min}) > max ({transceiver_eq_config.pre_max}).")
            return False
        if transceiver_eq_config.post_min > transceiver_eq_config.post_max:
            logging.warning(f"PostCursor range error! You entered min ({transceiver_eq_config.post_min}) > max ({transceiver_eq_config.post_max}).")
            return False
        if transceiver_eq_config.amp_max > 7 or transceiver_eq_config.pre_max > 7 or transceiver_eq_config.post_max > 7:
            logging.warning(f"Max > 7 error! amp_max: {transceiver_eq_config.amp_max}, pre_max: {transceiver_eq_config.pre_max}, post_max: {transceiver_eq_config.post_max}")
            return False
        if transceiver_eq_config.amp_min < 0 or transceiver_eq_config.pre_min < 0 or transceiver_eq_config.post_min < 0:
            logging.warning(f"Min < 0 error! amp_min: {transceiver_eq_config.amp_min}, pre_min: {transceiver_eq_config.pre_min}, post_min: {transceiver_eq_config.post_min}")
            return False
        return True
    
    async def connect(self):
        self.tester_obj = await testers.L23Tester(host=self.chassis_ip, username=self.username, password=self.password, port=self.tcp_port, enable_logging=self.enable_comm_trace)

        # Get logger
        logger = logging.getLogger(self.logger_name)
        logger.info(f"#####################################################################")
        logger.info(f"Chassis:              {self.chassis_ip}")
        logger.info(f"Username:             {self.username}")
        logger.info(f"Port Pair:           {self.port_pair_list}")
        logger.info(f"Lane:                 {self.lane}")
        logger.info(f"Amplitude Range:      [{self.amp_min}, {self.amp_max}] dB")
        logger.info(f"PreCursor Range:      [{self.pre_min}, {self.pre_max}] dB")
        logger.info(f"PostCursor Range:     [{self.post_min}, {self.post_max}] dB")
        logger.info(f"Delay After Reset:    {self.delay_after_reset} seconds")
        logger.info(f"Delay After EQ Write: {self.delay_after_eq_write} seconds")
        logger.info(f"PRBS Duration:        {self.prbs_duration} seconds")
        logger.info(f"#####################################################################")

    async def disconnect(self):
        await self.tester_obj.session.logoff()

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

        # exhaustive search of all cursor combinations
        for tx_port_obj, rx_port_obj in zip(tx_port_list, rx_port_list):
            __polynomial = self.prbs_polynomial

            # configure prbs
            await tx_port_obj.pcs_pma.prbs_config.type.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=__polynomial, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.ACCUMULATIVE)
            await rx_port_obj.pcs_pma.prbs_config.type.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=__polynomial, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.ACCUMULATIVE)

            # start prbs
            _serdes = self.lane - 1
            await tx_port_obj.l1.serdes[_serdes].prbs.control.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSON, error_on_off=enums.ErrorOnOff.ERRORSOFF)

            logger.info(f"-- Port Pair: {tx_port_obj.kind.module_id}/{tx_port_obj.kind.port_id} -> {rx_port_obj.kind.module_id}/{rx_port_obj.kind.port_id} --")
            result = []
            for amp_db in range(self.amp_min, self.amp_max+1):
                for pre_db in range(self.pre_min, self.pre_max+1):
                    for post_db in range(self.post_min, self.post_max+1):
                        await output_eq_write(port=rx_port_obj, lane=self.lane, db=amp_db, cursor=Cursor.AMPLITUDE, logger_name=self.logger_name)
                        await output_eq_write(port=rx_port_obj, lane=self.lane, db=pre_db, cursor=Cursor.PRECURSOR, logger_name=self.logger_name)
                        await output_eq_write(port=rx_port_obj, lane=self.lane, db=post_db, cursor=Cursor.POSTCURSOR, logger_name=self.logger_name)
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
                        logger.info(f"Amplitude: {amp_db} dB, PreCursor: {pre_db} dB, PostCursor: {post_db} dB, PRBS BER: {prbs_ber}")

                        # remember the result
                        result.append({"amp": amp_db, "pre": pre_db, "post": post_db, "prbs_ber": prbs_ber})

            # stop prbs
            _serdes = self.lane - 1
            await tx_port_obj.l1.serdes[_serdes].prbs.control.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSOFF, error_on_off=enums.ErrorOnOff.ERRORSOFF)

            # find the best
            sorted_result = sorted(result, key = lambda x: x["prbs_ber"])
            logger.info(f"Final sorted results:")
            for i in sorted_result:
                logger.info(f"Amplitude: {i['amp']} dB, PreCursor: {i['pre']} dB, PostCursor: {i['post']} dB, PRBS BER: {i['prbs_ber']}")
            
    
    async def run(self):
        self.validate_lane()
        self.validate_transceiver_eq_config(self.test_config.transceiver_eq_config)
        await self.connect()
        await self.exhaustive_search(self.port_pair_list)        
        await self.disconnect()
    


#---------------------------
# main()
#---------------------------
async def main():
    stop_event = asyncio.Event()
    try:
        test = CablePerfOptimalTest("cable_optimal_test_config.yml")
        await test.run()
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    asyncio.run(main())