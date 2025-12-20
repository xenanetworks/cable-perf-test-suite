# *************************************
# author: leonard.yu@teledyne.com
# *************************************

import asyncio
from xoa_driver import testers, modules, ports, enums, utils
from xoa_driver.misc import Hex
from xoa_driver.hlfuncs import mgmt
from .enums import *
import logging
from typing import List, Any, Union, Dict, Tuple
import time, os

type FreyaEdunModule = Union[modules.Z800FreyaModule, modules.Z1600EdunModule]
type FreyaEdunPort = Union[ports.Z800FreyaPort, ports.Z1600EdunPort]


# *************************************************************************************
# func: read_prbs_ber
# description: Read PRBS BER from a specified lane
# *************************************************************************************
async def read_prbs_ber(port: FreyaEdunPort, lane: int, logger_name: str) -> float:
    """Read PRBS BER from a specified lane. If zero errored bits, the BER is calculated as 4.6/prbs_bits for 99% confidence level.
    Read more in https://www.lightwaveonline.com/home/article/16647704/explaining-those-ber-testing-mysteries
    """
    # Get logger
    logger = logging.getLogger(logger_name)

    assert 1<=lane<=8
    # read starting PRBS BER
    _prbs_ber = 0.0
    _serdes = lane - 1
    resp = await port.layer1.serdes[_serdes].prbs.status.get()
    _prbs_bits = resp.byte_count * 8
    _prbs_errors = resp.error_count
    if _prbs_errors == 0:
        # _prbs_ber = 4.6/_prbs_bits
        _prbs_ber = 0
        logger.info(f"  PRBS BER [{lane}]: < {'{0:.3e}'.format(_prbs_ber)}")
    else:
        _prbs_ber = _prbs_errors/_prbs_bits
        logger.info(f"  PRBS BER [{lane}]: {'{0:.3e}'.format(_prbs_ber)}")
    return _prbs_ber

    
# *************************************************************************************
# func: less_equal
# description: Compare true if current is less than or equal to target
# *************************************************************************************
def less_equal(current: float, target:float) -> bool:
    if current <= target:
        return True
    else:
        return False
    
# *************************************************************************************
# func: test_done
# description: Show test result and stop PRBS
# *************************************************************************************
async def test_done(port: FreyaEdunPort, lane: int, current_ber: float, target_ber: float, amp_db: int, pre_db: int, post_db: int, is_successful: bool, logger_name: str):
    """Show test result and stop PRBS
    """
    # Get logger
    logger = logging.getLogger(logger_name)
    logger.info(f"#####################################################################")
    logger.info(f"Lane: {lane}")
    logger.info(f"Current PRBS BER: {'{0:.3e}'.format(current_ber)}, Target PRBS BER: {target_ber}")
    logger.info(f"{'SUCCESS' if is_successful else 'FAILED'}: amp = {amp_db} dB, pre = {pre_db} dB, post = {post_db} dB")
    logger.info(f"#####################################################################")

    # stop PRBS on port
    _serdes = lane - 1
    await port.layer1.serdes[_serdes].prbs.control.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSOFF, error_on_off=enums.ErrorOnOff.ERRORSOFF)

# *************************************************************************************
# func: get_port_list
# description: Get port object list from the port pair list
# *************************************************************************************
def get_port_obj_list(tester_obj: testers.L23Tester, port_pair_list: List[Dict[str, str]], key_str: str) -> List[FreyaEdunPort]:
    """Get port object list from the port pair list
    """
    _port_obj_list: List[FreyaEdunPort] = []
    for port_pair in port_pair_list:
        _port_str = port_pair[key_str]

        # Access module on the tester
        _mid = int(_port_str.split("/")[0])
        _pid = int(_port_str.split("/")[1])
        module_obj = tester_obj.modules.obtain(_mid)

        if not isinstance(module_obj, modules.Z800FreyaModule) and not isinstance(module_obj, modules.Z1600EdunModule):
            logging.info(f"This script is only for Freya & Edun module")
            return []

        # Get the port on module as TX port
        port_obj = module_obj.ports.obtain(_pid)

        # Inset the port object to the list
        _port_obj_list.append(port_obj)
    return _port_obj_list

# *************************************************************************************
# func: reserve_ports_in_list
# description: Reserve ports in the port object list
# *************************************************************************************
async def reserve_reset_ports_in_list(tester_obj: testers.L23Tester, port_obj_list: List[FreyaEdunPort]) -> None:
    """Reserve ports in the port object list
    """
    for _port in port_obj_list:
        _module_id = _port.kind.module_id
        _module = tester_obj.modules.obtain(_module_id)
        await mgmt.release_module(module=_module, should_release_ports=False)
        await mgmt.reserve_port(_port, reset=True)
    await asyncio.sleep(1.0)

# *************************************************************************************
# func: release_ports_in_list
# description: Release ports in the port object list
# *************************************************************************************
async def release_ports_in_list(port_obj_list: List[FreyaEdunPort]) -> None:
    """Release ports in the port object list
    """
    for _port in port_obj_list:
        await mgmt.release_port(_port)
    await asyncio.sleep(1.0)

# *************************************************************************************
# func: create_report_dir
# description: Create report directory
# *************************************************************************************
async def create_report_dir() -> str:
    datetime = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    path = "xena_cpom_" + datetime
    if not os.path.exists(path):
        os.makedirs(path)
    return path


# *************************************************************************************
# func: change_module_media
# description: Change module media and port speed
# *************************************************************************************
async def change_module_media(tester_obj: testers.L23Tester, module_list: List[int], media: enums.MediaConfigurationType, port_speed: str, logger_name: str) -> None:

    # Get logger
    logger = logging.getLogger(logger_name)
    logger.info(f"Configuring test module {module_list} to {media.name} {port_speed}")

    _port_count = int(port_speed.split("x")[0])
    _port_speed = int(port_speed.split("x")[1].replace("G", ""))*1000

    for _module_id in module_list:
        _module = tester_obj.modules.obtain(_module_id)
        await mgmt.release_module(module=_module, should_release_ports=True)
        await mgmt.reserve_module(module=_module)
        await mgmt.set_module_media_config(module=_module, media=media)
        await mgmt.set_module_port_config(module=_module, port_count=_port_count, port_speed=_port_speed,)


# *************************************************************************************
# func: get_tx_tap_value
# description: Get the TX tap value from the tx_taps list. 
# -1 means pre1, -2 means pre2, 0 means main, 1 means post1, 2 means post2
# *************************************************************************************
async def read_single_tx_tap_value(port: FreyaEdunPort, serdes_index: int, tap_index: int, num_txeq_pre: int, num_txeq_post: int, tx_taps_max: List[int], tx_taps_min: List[int]) -> Tuple[int, int, int]:
    """Get one Tx tap value from the port.
    -1 means pre1, -2 means pre2, 0 means main, 1 means post1, 2 means post2

    :return: (tap_value, tap_max, tap_min)
    """
    resp = await port.layer1.serdes[serdes_index].medium.tx.native.get()
    tx_taps = resp.tap_values
    
    if tap_index < 0 and abs(tap_index) > num_txeq_pre:
        raise ValueError("Invalid TXEQ_PRE tap index")
    if tap_index > 0 and tap_index > num_txeq_post:
        raise ValueError("Invalid TXEQ_POST tap index")
    
    _index = 0
    if tap_index == 0:
        _index = num_txeq_pre
    elif tap_index < 0:
        _index = num_txeq_pre + tap_index
    else:
        _index = num_txeq_pre + tap_index
    return (tx_taps[_index], tx_taps_max[_index], tx_taps_min[_index])


async def read_tx_taps_on_lanes(port: FreyaEdunPort, lanes: List[int]) -> List[List[int]]:
    """Get TX tap value from the tx_taps list.
    -1 means pre1, -2 means pre2, 0 means main, 1 means post1, 2 means post2
    """
    cmd_list = []
    for lane in lanes:
        _serdes_index = lane - 1
        cmd_list.append(
            port.layer1.serdes[_serdes_index].medium.tx.native.get()
        )

    resps = await utils.apply(*cmd_list)
    tx_taps = []
    for resp in resps:
        tx_taps.append(resp.tap_values)
    return tx_taps


async def change_tx_tap_on_lanes(port: FreyaEdunPort, lanes: List[int], tap_index: int, num_txeq_pre: int, num_txeq_post: int, tx_taps_max: List[int], tx_taps_min: List[int], mode: str) -> List[int]:
    """Increase one Tx tap value by step.
    -1 means pre1, -2 means pre2, 0 means main, 1 means post1, 2 means post2
    """
    if tap_index < 0 and abs(tap_index) > num_txeq_pre:
        raise ValueError("Invalid TXEQ_PRE tap index")
    if tap_index > 0 and tap_index > num_txeq_post:
        raise ValueError("Invalid TXEQ_POST tap index")
    
    max_sum = 0
    if isinstance(port, ports.Z800FreyaPort):
        max_sum = 87
    elif isinstance(port, ports.Z1600EdunPort):
        max_sum = 168

    cmd_list = []
    for lane in lanes:
        _serdes_index = lane - 1
        cmd_list.append(
            port.layer1.serdes[_serdes_index].medium.tx.native.get()
        )
    resps = await utils.apply(*cmd_list)
    
    tx_taps_list = [resp.tap_values for resp in resps]

    results = []
    for tx_taps in tx_taps_list:
        idx = tx_taps_list.index(tx_taps)
        serdes_index = lanes[idx] - 1
        current_sum = sum(abs(i) for i in tx_taps)
        if current_sum >= max_sum:
            pass
        else:
            _index = 0
        if tap_index == 0:
            _index = num_txeq_pre
        elif tap_index < 0:
            _index = num_txeq_pre + tap_index
        else:
            _index = num_txeq_pre + tap_index

        if mode == "inc":
            if tap_index == -1 or tap_index == 1:
                if tx_taps[_index] <= tx_taps_min[_index]:
                    pass
                else:
                    tx_taps[_index] -= 1
                    await port.layer1.serdes[serdes_index].medium.tx.native.set(tap_values=tx_taps)
                    results.append(lanes[idx])
            else:
                if tx_taps[_index] >= tx_taps_max[_index]:
                    pass
                else:
                    tx_taps[_index] += 1
                    await port.layer1.serdes[serdes_index].medium.tx.native.set(tap_values=tx_taps)
                    results.append(lanes[idx])
        elif mode == "dec":
            if tap_index == -1 or tap_index == 1:
                if tx_taps[_index] >= tx_taps_max[_index]:
                    pass
                else:
                    tx_taps[_index] += 1
                    await port.layer1.serdes[serdes_index].medium.tx.native.set(tap_values=tx_taps)
                    results.append(lanes[idx])
            else:
                if tx_taps[_index] <= tx_taps_min[_index]:
                    pass
                else:
                    tx_taps[_index] -= 1
                    await port.layer1.serdes[serdes_index].medium.tx.native.set(tap_values=tx_taps)
                    results.append(lanes[idx])
        else:
            pass
    return results

    
async def start_prbs_on_lanes(port: FreyaEdunPort, lanes: List[int], logger_name: str) -> None:
    """Start PRBS on a specified lane
    """
    # Get logger
    logger = logging.getLogger(logger_name)

    # start prbs on a lane
    logger.info(f"Starting PRBS on Port {port.kind.module_id}/{port.kind.port_id} on Lanes {lanes}")

    cmd_list = []
    for lane in lanes:
        _serdes_index = lane - 1
        cmd_list.append(
            port.layer1.serdes[_serdes_index].prbs.control.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSON, error_on_off=enums.ErrorOnOff.ERRORSOFF)
        )
    await utils.apply(*cmd_list)


async def stop_prbs_on_lanes(port: FreyaEdunPort, lanes: List[int], logger_name: str) -> None:
    """Stop PRBS on a specified lane
    """
    # Get logger
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

async def load_preset_tx_tap_values(port: FreyaEdunPort, lanes: List[int], preset_tap_values: List[int], logger_name: str) -> None:
    """Load preset TX tap values to the port
    """
    # Get logger
    logger = logging.getLogger(logger_name)

    # stop prbs on a lane
    logger.info(f"Loading preset TX tap values {preset_tap_values} on Port {port.kind.module_id}/{port.kind.port_id} on Lane {lanes}")

    cmd_list = []
    for lane in lanes:
        _serdes_index = lane - 1
        cmd_list.append(
            port.layer1.serdes[_serdes_index].medium.tx.native.set(tap_values=preset_tap_values)
        )
    await utils.apply(*cmd_list)

async def read_prbs_bers(port: FreyaEdunPort, lanes: List[int], logger_name: str) -> List[float]:
    """Read PRBS BER from a specified lane. If zero errored bits, the BER is calculated as 4.6/prbs_bits for 99% confidence level.
    Read more in https://www.lightwaveonline.com/home/article/16647704/explaining-those-ber-testing-mysteries
    """
    # Get logger
    logger = logging.getLogger(logger_name)

    _prbs_ber = 0.0
    
    cmd_list = []
    for lane in lanes:
        _serdes_index = lane - 1
        cmd_list.append(
            port.layer1.serdes[_serdes_index].prbs.status.get()
        )

    resps = await utils.apply(*cmd_list)
    results = []
    for i in range(len(resps)):
        _prbs_bits = resps[i].byte_count * 8
        _prbs_errors = resps[i].error_count
        if _prbs_bits == 0:
            logger.info(f"  PRBS BER [{lanes[i]}]: N/A (No bits sent)")
            results.append(-1)
            continue
        if _prbs_errors == 0:
            _prbs_ber = 4.6/_prbs_bits
            # _prbs_ber = 0
            logger.info(f"  PRBS BER [{lanes[i]}]: < {'{0:.3e}'.format(_prbs_ber)}")
        else:
            _prbs_ber = _prbs_errors/_prbs_bits
            logger.info(f"  PRBS BER [{lanes[i]}]: {'{0:.3e}'.format(_prbs_ber)}")
        results.append(_prbs_ber)
    
    return results


def get_lanes_to_optimize(prbs_bers: List[float], target_ber: float) -> List[int]:
    """Get lanes that need to be optimized based on current PRBS BER and target BER
    """
    lanes_to_optimize = []
    for prbs_ber in prbs_bers:
        if prbs_ber > target_ber:
            lanes_to_optimize.append(prbs_bers.index(prbs_ber))
    return lanes_to_optimize

def update_last_prbs_bers_for_opt_lanes(last_prbs_bers: List[float], lanes_to_optimize: List[int], original_lanes: List[int]) -> List[float]:
    """Update last PRBS BERs for the lanes that have been optimized
    """
    # difference between original_lanes and lanes_to_optimize
    for lane in original_lanes:
        if lane not in lanes_to_optimize:
            idx = original_lanes.index(lane)
            last_prbs_bers[idx] = -1
    # remove all -1 from last_prbs_bers
    while -1 in last_prbs_bers:
        last_prbs_bers.remove(-1)
    return last_prbs_bers
