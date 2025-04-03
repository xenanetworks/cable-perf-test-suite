# *************************************
# author: leonard.yu@teledyne.com
# *************************************

import asyncio
from xoa_driver import testers, modules, ports, enums
from xoa_driver.misc import Hex
from xoa_driver.hlfuncs import mgmt
from .enums import *
import logging
import math
from typing import List, Any
import time, os

# *************************************************************************************
# func: read_prbs_ber
# description: Read PRBS BER from a specified lane
# *************************************************************************************
async def read_prbs_ber(port: ports.Z800FreyaPort, lane: int, logger_name: str) -> float:
    """Read PRBS BER from a specified lane. If zero errored bits, the BER is calculated as 4.6/prbs_bits for 99% confidence level.
    Read more in https://www.lightwaveonline.com/home/article/16647704/explaining-those-ber-testing-mysteries
    """
    # Get logger
    logger = logging.getLogger(logger_name)

    assert 1<=lane<=8
    # read starting PRBS BER
    _prbs_ber = 0.0
    _serdes = lane - 1
    resp = await port.serdes[_serdes].prbs.status.get()
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
async def test_done(port: ports.Z800FreyaPort, lane: int, current_ber: float, target_ber: float, amp_db: int, pre_db: int, post_db: int, is_successful: bool, logger_name: str):
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
    await port.serdes[_serdes].prbs.control.set(prbs_seed=17, prbs_on_off=enums.PRBSOnOff.PRBSOFF, error_on_off=enums.ErrorOnOff.ERRORSOFF)

# *************************************************************************************
# func: get_port_list
# description: Get port object list from the port pair list
# *************************************************************************************
def get_port_list(tester_obj: testers.L23Tester, port_pair_list: List[dict], key_str: str) -> List[Any]:
    """Get port object list from the port pair list
    """
    _port_obj_list = []
    for port_pair in port_pair_list:
        _port_str = port_pair[key_str]

        # Access module on the tester
        _mid = int(_port_str.split("/")[0])
        _pid = int(_port_str.split("/")[1])
        module_obj = tester_obj.modules.obtain(_mid)

        if not isinstance(module_obj, modules.Z800FreyaModule):
            logging.info(f"This script is only for Freya module")
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
async def reserve_reset_ports_in_list(tester_obj: testers.L23Tester, port_obj_list: List[ports.Z800FreyaPort]) -> None:
    """Reserve ports in the port object list
    """
    for _port in port_obj_list:
        _module_id = _port.kind.module_id
        _module = tester_obj.modules.obtain(_module_id)
        await mgmt.free_module(module=_module, should_free_ports=False)
        await mgmt.reserve_port(_port)
        await mgmt.reset_port(_port)
    await asyncio.sleep(1.0)

# *************************************************************************************
# func: release_ports_in_list
# description: Release ports in the port object list
# *************************************************************************************
async def release_ports_in_list(port_obj_list: List[ports.Z800FreyaPort]) -> None:
    """Release ports in the port object list
    """
    for _port in port_obj_list:
        await mgmt.free_port(_port)
    await asyncio.sleep(1.0)

# *************************************************************************************
# func: create_report_dir
# description: Create report directory
# *************************************************************************************
async def create_report_dir(tester_obj: testers.L23Tester) -> str:
    datetime = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    path = "xena_cable_eq_perf_optimization_" + datetime
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
    logger.info(f"=============== Change Module Media and Port Speed ====================")
    logger.info(f"{'Tester:':<20}{tester_obj.info.host}")
    logger.info(f"{'Username:':<20}{tester_obj.session.owner_name}")
    logger.info(f"{'Media:':<20}{media.name}")
    logger.info(f"{'Port Speed:':<20}{port_speed}")

    _port_count = int(port_speed.split("x")[0])
    _port_speed = int(port_speed.split("x")[1].replace("G", ""))
    _port_speed_config = [_port_speed*1000] * _port_count
    _port_speed_config.insert(0, _port_count)
    for _module_id in module_list:
        _module = tester_obj.modules.obtain(_module_id)
        await mgmt.free_module(module=_module, should_free_ports=True)
        await mgmt.reserve_module(module=_module)
        await _module.media.set(media_config=media)
        await _module.cfp.config.set(portspeed_list=_port_speed_config)

    logger.info(f"=============== Done ====================")