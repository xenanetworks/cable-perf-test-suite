################################################################
#
#                   TARGET CABLE PERFORMANCE
#
# This script uses a target value to find the locally optimal 
# transceiver cursor value combination. When the measured 
# PRBS BER value is less that the target, the search will stop.
#
################################################################


import asyncio

from xoa_driver import testers, modules, ports, enums
from xoa_driver.hlfuncs import mgmt
from libs import *
from models import *
import yaml, json
from pathlib import Path
import logging


#-----------------------------
# class CablePerfTargetTest
#-----------------------------

class CablePerfTargetTest:
    def __init__(self, test_config_file: str, enable_comm_trace: bool = False):
        self.enable_comm_trace = enable_comm_trace
        self.test_config_file = test_config_file
        self.test_config: CablePerfTargetTestConfig
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
    def amp_init(self):
        return self.test_config.transceiver_init_config.amp_init
    
    @property
    def pre_init(self):
        return self.test_config.transceiver_init_config.pre_init
    
    @property
    def post_init(self):
        return self.test_config.transceiver_init_config.post_init
    
    @property
    def target_prbs_ber(self):
        return self.test_config.transceiver_init_config.target_prbs_ber
    
    @property
    def delay_after_reset(self):
        return self.test_config.delay_after_reset
    
    @property
    def lane(self):
        return self.test_config.lane
    
    @property
    def delay_after_eq_write(self):
        return self.test_config.transceiver_init_config.delay_after_eq_write
    
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
            test_config_value = json.dumps(test_config_dict["cable_target_test_config"])
            self.test_config = CablePerfTargetTestConfig.model_validate_json(test_config_value)

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

    def validate_transceiver_eq_config(self, transceiver_init_config: TransceiverInitConfig) -> bool:
        if transceiver_init_config.amp_init < 0 or transceiver_init_config.pre_init < 0 or transceiver_init_config.post_init < 0:
            logging.warning(f"Min < 0 error! amp_init: {transceiver_init_config.amp_init}, pre_init: {transceiver_init_config.pre_init}, post_init: {transceiver_init_config.post_init}")
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
        logger.info(f"Amplitude Init:      {self.amp_init} dB")
        logger.info(f"PreCursor Init:      {self.pre_init} dB")
        logger.info(f"PostCursor Init:     {self.post_init} dB")
        logger.info(f"Target PRBS BER:     {self.target_prbs_ber}")
        logger.info(f"Delay After Reset:    {self.delay_after_reset} seconds")
        logger.info(f"Delay After EQ Write: {self.delay_after_eq_write} seconds")
        logger.info(f"PRBS Duration:        {self.prbs_duration} seconds")
        logger.info(f"#####################################################################")

    async def disconnect(self):
        await self.tester_obj.session.logoff()

    async def target_search(self, port_pair_list: List[dict]):
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
            
            # write amp/pre/post to initial dB as a starting point
            _amp_db = self.amp_init
            _pre_db = self.pre_init
            _post_db = self.post_init
            logger.info(f"|----------------------|")
            logger.info(f"|  Initial dB Values   |")
            logger.info(f"|----------------------|")
            await output_eq_write(port=rx_port_obj, lane=self.lane, db=_amp_db, cursor=Cursor.AMPLITUDE, logger_name=self.logger_name)
            await output_eq_write(port=rx_port_obj, lane=self.lane, db=_pre_db, cursor=Cursor.PRECURSOR, logger_name=self.logger_name)
            await output_eq_write(port=rx_port_obj, lane=self.lane, db=_post_db, cursor=Cursor.POSTCURSOR, logger_name=self.logger_name)
            await asyncio.sleep(self.delay_after_eq_write)

            # check if PRBS BER is less equal to target BER
            _current_prbs_ber = await read_prbs_ber(port=rx_port_obj, lane=self.lane, logger_name=self.logger_name)
            if less_equal(_current_prbs_ber, self.target_prbs_ber):
                await test_done(tx_port_obj, self.lane, _current_prbs_ber, self.target_prbs_ber, _amp_db, _pre_db, _post_db, is_successful=True, logger_name=self.logger_name)
                return
            else:
                _prev_prbs_ber = _current_prbs_ber

                # algorithm - adjust amplitude and check PRBS stats on port 1
                logger.info(f"|----------------------|")
                logger.info(f"|   Adjust AMPLITUDE   |")
                logger.info(f"|----------------------|")
                while _amp_db<7:
                    _amp_db += 1
                    await output_eq_write(port=rx_port_obj, lane=self.lane, db=_amp_db, cursor=Cursor.AMPLITUDE, logger_name=self.logger_name)
                    await asyncio.sleep(self.delay_after_eq_write)

                    # read the current BER
                    _current_prbs_ber = await read_prbs_ber(port=rx_port_obj, lane=self.lane, logger_name=self.logger_name)
                    
                    # if current BER <= target BER, mark done and finish
                    if less_equal(_current_prbs_ber, self.target_prbs_ber):
                        await test_done(tx_port_obj, self.lane, _current_prbs_ber, self.target_prbs_ber, _amp_db, _pre_db, _post_db, is_successful=True, logger_name=self.logger_name)
                        return
                    # if target BER < current BER <= prev BER, continue the searching
                    elif less_equal(_current_prbs_ber, _prev_prbs_ber):
                        _prev_prbs_ber = _current_prbs_ber
                        continue
                    # if current BER > prev BER, roll back and move on to pre-cursor
                    else:
                        _amp_db -= 1
                        await output_eq_write(port=rx_port_obj, lane=self.lane, db=_amp_db, cursor=Cursor.AMPLITUDE, logger_name=self.logger_name)
                        break
                await asyncio.sleep(self.delay_after_eq_write)

                # algorithm - adjust pre-cursor and check PRBS stats on port 1
                logger.info(f"|----------------------|")
                logger.info(f"|   Adjust PRE-CURSOR  |")
                logger.info(f"|----------------------|")
                while _pre_db<7:
                    _pre_db += 1
                    await output_eq_write(port=rx_port_obj, lane=self.lane, db=_pre_db, cursor=Cursor.PRECURSOR, logger_name=self.logger_name)
                    await asyncio.sleep(self.delay_after_eq_write)

                    # read the current BER
                    _current_prbs_ber = await read_prbs_ber(port=rx_port_obj, lane=self.lane, logger_name=self.logger_name)
                    
                    # if current BER <= target BER, mark done and finish
                    if less_equal(_current_prbs_ber, self.target_prbs_ber):
                        await test_done(tx_port_obj, self.lane, _current_prbs_ber, self.target_prbs_ber, _amp_db, _pre_db, _post_db, is_successful=True, logger_name=self.logger_name)
                        return
                    # if target BER < current BER <= prev BER, continue the searching
                    elif less_equal(_current_prbs_ber, _prev_prbs_ber):
                        _prev_prbs_ber = _current_prbs_ber
                        continue
                    # if current BER > prev BER, roll back and move on to pre-cursor
                    else:
                        _pre_db -= 1
                        await output_eq_write(port=rx_port_obj, lane=self.lane, db=_pre_db, cursor=Cursor.PRECURSOR, logger_name=self.logger_name)
                        break
                await asyncio.sleep(self.delay_after_eq_write)

                # algorithm - adjust post-cursor and check PRBS stats on port 1
                logger.info(f"|----------------------|")
                logger.info(f"|  Adjust POST-CURSOR  |")
                logger.info(f"|----------------------|")
                while _post_db<7:
                    _post_db += 1
                    await output_eq_write(port=rx_port_obj, lane=self.lane, db=_post_db, cursor=Cursor.POSTCURSOR, logger_name=self.logger_name)
                    await asyncio.sleep(self.delay_after_eq_write)

                    # read the current BER
                    _current_prbs_ber = await read_prbs_ber(port=rx_port_obj, lane=self.lane, logger_name=self.logger_name)
                    
                    # if current BER <= target BER, mark done and finish
                    if less_equal(_current_prbs_ber, self.target_prbs_ber):
                        await test_done(tx_port_obj, self.lane, _current_prbs_ber, self.target_prbs_ber, _amp_db, _pre_db, _post_db, is_successful=True, logger_name=self.logger_name)
                        return
                    # if target BER < current BER <= prev BER, continue the searching
                    elif less_equal(_current_prbs_ber, _prev_prbs_ber):
                        _prev_prbs_ber = _current_prbs_ber
                        continue
                    # if current BER > prev BER, roll back and move on to pre-cursor
                    else:
                        _post_db -= 1
                        await output_eq_write(port=rx_port_obj, lane=self.lane, db=_post_db, cursor=Cursor.POSTCURSOR, logger_name=self.logger_name)
                        break
                await asyncio.sleep(self.delay_after_eq_write)

                # searching failed
                # read the current BER
                _current_prbs_ber = await read_prbs_ber(port=rx_port_obj, lane=self.lane, logger_name=self.logger_name)
                await test_done(tx_port_obj, self.lane, _current_prbs_ber, self.target_prbs_ber, _amp_db, _pre_db, _post_db, is_successful=False, logger_name=self.logger_name)
            
    
    async def run(self):
        self.validate_lane()
        self.validate_transceiver_eq_config(self.test_config.transceiver_init_config)
        await self.connect()
        await self.target_search(self.port_pair_list)        
        await self.disconnect()
    


#---------------------------
# main()
#---------------------------
async def main():
    stop_event = asyncio.Event()
    try:
        test = CablePerfTargetTest("cable_target_test_config.yml")
        await test.run()
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    asyncio.run(main())