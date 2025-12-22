# *************************************
# author: leonard.yu@teledyne.com
# *************************************

import asyncio
from xoa_driver import testers, modules, ports, enums, utils
from xoa_driver.misc import Hex
from xoa_driver.hlfuncs import mgmt
from .enums import *
import logging
from typing import(List, Any, Union, Dict, Tuple, TYPE_CHECKING)
import time, os
from dataclasses import dataclass

type FreyaEdunModule = Union[modules.Z800FreyaModule, modules.Z1600EdunModule]
type FreyaEdunPort = Union[ports.Z800FreyaPort, ports.Z1600EdunPort]

if TYPE_CHECKING:
    from xoa_driver.lli import commands as llicmds


# *************************************************************************************
# func: config_prbs
# description: Configure PRBS on the port
# *************************************************************************************
async def config_prbs(ports: List[FreyaEdunPort], pattern: enums.PRBSPolynomial, logger_name: str) -> None:
    """Configure PRBS on the port. 
    
    Default settings: PRBS inserted type = PHY_LINE, invert = NON_INVERTED, statistics mode = ACCUMULATIVE

    :param port: Port object
    :type port: FreyaEdunPort
    :param pattern: PRBS polynomial type
    :type pattern: enums.PRBSPolynomial
    :param logger_name: Logger name
    :type logger_name: str
    """
    
    logger = logging.getLogger(logger_name)
    logger.info(f"Configuring PRBS to {pattern.name}")
    for port in ports:
        await port.layer1.prbs_config.set(prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE, polynomial=pattern, invert=enums.PRBSInvertState.NON_INVERTED, statistics_mode=enums.PRBSStatisticsMode.ACCUMULATIVE)
    await asyncio.sleep(1)


# *************************************************************************************
# func: run_prbs_on_lanes
# description: Measure PRBS BER on lanes.
# *************************************************************************************
async def run_prbs_on_lanes(port: FreyaEdunPort, lanes: List[int], duration: int, logger_name: str) -> None:
    """Run PRBS on lanes

    :param port: Port object
    :type port: FreyaEdunPort
    :param lanes: List of lane numbers
    :type lanes: List[int]
    :param duration: Duration to measure PRBS in seconds
    :type duration: int
    :param logger_name: Logger name
    :type logger_name: str
    """
    
    logger = logging.getLogger(logger_name)

    # start prbs on a lane
    logger.info(f"Starting PRBS on Port {port.kind.module_id}/{port.kind.port_id} on Lanes {lanes}")

    start_cmd_list = []
    stop_cmd_list = []
    for lane in lanes:
        _serdes_index = lane - 1
        start_cmd_list.append(
            port.layer1.serdes[_serdes_index].prbs.control.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSON, error_on_off=enums.ErrorOnOff.ERRORSOFF)
        )
        stop_cmd_list.append(
            port.layer1.serdes[_serdes_index].prbs.control.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSOFF, error_on_off=enums.ErrorOnOff.ERRORSOFF)
        )
    await utils.apply(*start_cmd_list)

    logger.info(f"Measuring PRBS for {duration}s")
    await asyncio.sleep(duration)

    # stop prbs on a lane
    logger.info(f"Stopping PRBS on Port {port.kind.module_id}/{port.kind.port_id} on Lanes {lanes}")

    await utils.apply(*stop_cmd_list)
    await asyncio.sleep(1)

# *************************************************************************************
# func: stop_prbs_on_lanes
# description: Stop PRBS on lanes. 
# *************************************************************************************
async def stop_prbs_on_lanes(port: FreyaEdunPort, lanes: List[int], logger_name: str) -> None:
    """Stop PRBS on lanes

    :param port: Port object
    :type port: FreyaEdunPort
    :param lanes: List of lane numbers
    :type lanes: List[int]
    :param logger_name: Logger name
    :type logger_name: str
    """
    
    logger = logging.getLogger(logger_name)

    # stop prbs on a lane
    logger.info(f"Stopping PRBS on Port {port.kind.module_id}/{port.kind.port_id} on Lanes {lanes}")

    cmd_list = []
    for lane in lanes:
        _serdes_index = lane - 1
        cmd_list.append(
            port.layer1.serdes[_serdes_index].prbs.control.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSOFF, error_on_off=enums.ErrorOnOff.ERRORSOFF)
        )
    await utils.apply(*cmd_list)
    await asyncio.sleep(1)


# *************************************************************************************
# func: read_ber_from_lanes
# description: Read PRBS BER from the lanes.
# *************************************************************************************
async def read_ber_from_lanes(port: FreyaEdunPort, lanes: List[int], logger_name: str) -> List[Dict[str, Any]]:
    """Read the PRBS BER from the lanes

    :param port: Port object
    :type port: FreyaEdunPort
    :param lanes: List of lane numbers
    :type lanes: List[int]
    :param logger_name: Logger name
    :type logger_name: str
    :return: List of dictionaries containing {"lane": lane number, "prbs_ber": PRBS BER value}.
    :rtype: List[Dict[str, Any]]
    """
    
    logger = logging.getLogger(logger_name)

    _prbs_ber = 0.0
    
    cmd_list = []
    for _lane in lanes:
        _serdes_index = _lane - 1
        cmd_list.append(
            port.layer1.serdes[_serdes_index].prbs.status.get()
        )

    while True:
        resps = await utils.apply(*cmd_list)
        lock_status_lanes: List[enums.PRBSLockStatus] = [resp.lock for resp in resps]
        logger.debug(f"PRBS Lock Status: {[(lane, lock_status.name.lower().replace('prbs', '')) for lane, lock_status in zip(lanes, lock_status_lanes)]}")
        if all(lock_status == enums.PRBSLockStatus.PRBSOFF or lock_status == enums.PRBSLockStatus.PRBSOFFUNSTABLE for lock_status in lock_status_lanes):
            break
        await asyncio.sleep(1)

    results = []
    for _lane, _resp in zip(lanes, resps):
        _prbs_bits = _resp.byte_count * 8
        _prbs_errors = _resp.error_count
        _prbs_ber = 1
        if _prbs_bits == 0:
            logger.info(f"  PRBS BER [{_lane}]: N/A (No bits sent)")
            _prbs_ber = 1
        elif _prbs_errors == 0:
            _prbs_ber = 4.6/_prbs_bits
            # _prbs_ber = 0
            logger.info(f"  PRBS BER [{_lane}]: < {'{0:.3e}'.format(_prbs_ber)}")
        else:
            _prbs_ber = _prbs_errors/_prbs_bits
            logger.info(f"  PRBS BER [{_lane}]: {'{0:.3e}'.format(_prbs_ber)}")
        results.append({"lane": _lane, "prbs_ber": _prbs_ber})
    await asyncio.sleep(1)
    return results


# *************************************************************************************
# func: update_last_prbs_bers_for_opt_lanes
# description: Get lanes that need to be optimized based on current PRBS BER and target BER
# *************************************************************************************
def update_last_prbs_bers_for_opt_lanes(curr_best_bers: List[float], curr_lanes: List[int], reference_lanes: List[int]) -> List[float]:
    """Update the last PRBS BERs for optimized lanes

    :param curr_best_bers: the current best PRBS BER of the current lanes
    :type curr_best_bers: List[float]
    :param curr_lanes: the current lanes that read PRBS BER
    :type curr_lanes: List[int]
    :param reference_lanes: the reference lanes used for comparison
    :type reference_lanes: List[int]
    :return: updated list of current best PRBS BERs
    :rtype: List[float]
    """
    # difference between reference_lanes and curr_lanes
    curr_lanes_set = set(curr_lanes)
    for idx, _lane in enumerate(reference_lanes):
        if _lane not in curr_lanes_set:
            curr_best_bers[idx] = -1
    # remove all -1 from curr_best_bers
    while -1 in curr_best_bers:
        curr_best_bers.remove(-1)
    return curr_best_bers


# *************************************************************************************
# func: clear_prbs_counters
# description: Clear PRBS counters on all lanes
# *************************************************************************************
async def clear_prbs_counters(port: FreyaEdunPort, logger_name: str) -> None:
    """Clear PRBS counters on all lanes

    :param port: Port object
    :type port: FreyaEdunPort
    :param logger_name: Logger name
    :type logger_name: str
    """
    
    logger = logging.getLogger(logger_name)
    logger.info(f"Clearing PRBS counters")
    await port.layer1.pcs_fec.clear.set()
    await asyncio.sleep(1)


# *************************************************************************************
# func: get_below_target_lane_ber_dicts
# description: Get lanes that need to be optimized based on current PRBS BER and target BER
# *************************************************************************************
def get_below_target_lane_ber_dicts(lane_ber_dicts: List[Dict[str, Any]], target_ber: float, logger_name: str) -> List[Dict[str, Any]]:
    """Get the lane BER dicts that need to be optimized based on target BER

    :param lane_ber_dicts: List of dictionaries containing lane indices and their current PRBS BER values
    :type lane_ber_dicts: List[Dict[str, Any]]
    :param target_ber: Target BER value
    :type target_ber: float
    :param logger_name: Logger name
    :type logger_name: str
    :return: List of lane BER dicts that need to be optimized
    :rtype: List[Dict[str, Any]]
    """
    logger = logging.getLogger(logger_name)
    result = []
    sorted_lane_ber_dicts = sorted(lane_ber_dicts, key=lambda x: x["lane"])
    for lane_ber_dict in sorted_lane_ber_dicts:
        if lane_ber_dict["prbs_ber"] >= target_ber:
            result.append(lane_ber_dict)
        else:
            logger.info(f"Lane {lane_ber_dict['lane']}: PRBS BER {lane_ber_dict['prbs_ber']} < Target BER {target_ber}. Stopping optimization.")
    return result

# *************************************************************************************
# func: update_best_lane_ber_dicts
# description: Update the lane BER dicts with the best PRBS BER values
# *************************************************************************************
def update_best_lane_ber_dicts(lane_ber_dicts: List[Dict[str, Any]], best_lane_ber_dicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Update the lane BER dicts with the best PRBS BER values

    :param lane_ber_dicts: List of dictionaries containing lane indices and their current PRBS BER values
    :type lane_ber_dicts: List[Dict[str, Any]]
    :param best_lane_ber_dicts: List of dictionaries containing lane indices and their best PRBS BER values
    :type best_lane_ber_dicts: List[Dict[str, Any]]
    :return: List of lane BER dicts with the best PRBS BER values
    :rtype: List[Dict[str, Any]]
    """
    result = []
    sorted_lane_ber_dicts = sorted(lane_ber_dicts, key=lambda x: x["lane"])
    sorted_best_lane_ber_dicts = sorted(best_lane_ber_dicts, key=lambda x: x["lane"])
    for lane_ber_dict, best_lane_ber_dict in zip(sorted_lane_ber_dicts, sorted_best_lane_ber_dicts):
        if lane_ber_dict["prbs_ber"] <= best_lane_ber_dict["prbs_ber"]:
            result.append(lane_ber_dict)
        else:
            result.append(best_lane_ber_dict)
    return result

# *************************************************************************************
# func: get_worsen_lane_ber_dicts
# description: Get the lane BER dicts with the worst PRBS BER values
# *************************************************************************************
def get_worsen_lane_ber_dicts(lane_ber_dicts: List[Dict[str, Any]], best_lane_ber_dicts: List[Dict[str, Any]], logger_name: str) -> List[Dict[str, Any]]:
    """Get the lane BER dicts with the worst PRBS BER values

    :param lane_ber_dicts: List of dictionaries containing lane indices and their current PRBS BER values
    :type lane_ber_dicts: List[Dict[str, Any]]
    :param best_lane_ber_dicts: List of dictionaries containing lane indices and their best PRBS BER values
    :type best_lane_ber_dicts: List[Dict[str, Any]]
    :return: List of lane BER dicts with worsen PRBS BER values
    :rtype: List[Dict[str, Any]]
    """
    logger = logging.getLogger(logger_name)
    result = []
    sorted_lane_ber_dicts = sorted(lane_ber_dicts, key=lambda x: x["lane"])
    sorted_best_lane_ber_dicts = sorted(best_lane_ber_dicts, key=lambda x: x["lane"])
    for lane_ber_dict, best_lane_ber_dict in zip(sorted_lane_ber_dicts, sorted_best_lane_ber_dicts):
        if lane_ber_dict["prbs_ber"] > best_lane_ber_dict["prbs_ber"]:
            result.append(lane_ber_dict)
            logger.info(f"Lane {lane_ber_dict['lane']}: PRBS BER degrades from {best_lane_ber_dict['prbs_ber']} to {lane_ber_dict['prbs_ber']}. Revert to previous equalizer settings.")
    return result

# *************************************************************************************
# func: update_lane_ber_dicts
# description: Update lane BER dicts
# *************************************************************************************
def update_lane_ber_dicts(lane_ber_dicts: List[Dict[str, Any]], best_lane_ber_dicts: List[Dict[str, Any]], logger_name: str) -> List[Dict[str, Any]]:
    """Update lane BER dicts

    :param lane_ber_dicts: List of dictionaries containing lane indices and their current PRBS BER values
    :type lane_ber_dicts: List[Dict[str, Any]]
    :param best_lane_ber_dicts: List of dictionaries containing lane indices and their best PRBS BER values
    :type best_lane_ber_dicts: List[Dict[str, Any]]
    :return: List of lane BER dicts with worsen PRBS BER values
    :rtype: List[Dict[str, Any]]
    """
    logger = logging.getLogger(logger_name)
    result = []
    sorted_lane_ber_dicts = sorted(lane_ber_dicts, key=lambda x: x["lane"])
    sorted_best_lane_ber_dicts = sorted(best_lane_ber_dicts, key=lambda x: x["lane"])
    for lane_ber_dict, best_lane_ber_dict in zip(sorted_lane_ber_dicts, sorted_best_lane_ber_dicts):
        if lane_ber_dict["prbs_ber"] <= best_lane_ber_dict["prbs_ber"]:
            result.append(lane_ber_dict)
            logger.info(f"Lane {lane_ber_dict['lane']}: PRBS BER improves from {best_lane_ber_dict['prbs_ber']} to {lane_ber_dict['prbs_ber']}. Continue optimization.")
    return result