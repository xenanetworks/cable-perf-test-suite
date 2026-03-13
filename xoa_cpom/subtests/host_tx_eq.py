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
# class: XenaHostTxEqOptimization
# description: This class provides an automated optimization framework that uses 
# PRBS-based BER testing to test Host Tx Equalization for the best 
# possible signal integrity.
# *************************************************************************************
class XenaHostTxEqOptimization:
    """
    This class provides an automated optimization framework that uses PRBS-based BER testing to test Host Tx Equalization for the best possible signal integrity.
    """
    def __init__(self, tester_objs: List[testers.L23Tester], test_config: HostTxEqTestConfig, logger_name: str, report_filename: str):
        self.tester_objs = tester_objs
        self.test_config = test_config
        self.logger_name = logger_name
        self.report_filename = report_filename
        self.report_gen = HostTxEqTestReportGenerator(
            logger_name=self.logger_name, 
            name="Host Tx EQ Test", 
            chassis_list=[tester_obj.info.host for tester_obj in self.tester_objs])        

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
        for chassis_ip, module_ids in self.chassis_modules_dict.items():
            module_str_configs = []
            # print(f"{chassis_ip}: {module_ids}")
            for module_id in module_ids:
                module_str_configs.append((str(module_id), self.test_config.module_media, self.test_config.port_speed))
            tester_obj = find_tester_obj(chassis_ip, self.tester_objs)
            await config_modules(tester_obj, module_str_configs, self.logger_name)

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
        port_pair_obj_list = await convert_port_ids_to_objects(self.tester_objs, port_pair_list)  

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
        port_pair_obj_list = await convert_port_ids_to_objects(self.tester_objs, port_pair_list)  

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
    
