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
# func: convert_port_ids_to_objects
# description: Get the port objects from the port pair list
# *************************************************************************************
def convert_port_ids_to_objects(tester_obj: testers.L23Tester, port_pair_list: List[Dict[str, str]]) -> List[Dict[str, FreyaEdunPort]]:
    """Get the port objects from the port pair list

    :param tester_obj: The tester object
    :type tester_obj: testers.L23Tester
    :param port_pair_list: The list of port pairs as defined in the config file
    :type port_pair_list: List[Dict[str, str]]
    :return: List of port objects in the same order as the port pair list
    :rtype: List[Dict[str, GenericL23Port]]
    """
    port_obj_list: List[Dict[str, FreyaEdunPort]] = []
    for port_pair in port_pair_list:
        _txport,_rxport = mgmt.obtain_ports_by_ids(tester_obj, [port_pair["tx"], port_pair["rx"]])
        port_obj_list.append({"tx": _txport, "rx": _rxport}) # type: ignore
    return port_obj_list


# *************************************************************************************
# func: config_modules
# description: Configure modules with media and port speed
# *************************************************************************************
async def config_modules(tester_obj: testers.L23Tester, module_str_configs: List[Tuple[str, str, str]], logger_name: str) -> None:
    """Config each module in the list

    :param module_str_configs: Module string configuration list, each item is a tuple of (module id, module_media, port_config)
    :type module_str_configs: List[Tuple[str, str, str]]
    :param logger_name: the logger name
    :type logger_name: str
    """

    # Get logger
    logger = logging.getLogger(logger_name)
    module_configs =[]
    for module_config_str in module_str_configs:
        module_id, module_media_str, port_config_str = module_config_str
        module_obj = mgmt.obtain_modules_by_ids(tester_obj, [module_id])[0]
        module_media = enums.MediaConfigurationType[module_media_str]
        port_count = int(port_config_str.split('x')[0])
        port_speed = int(port_config_str.split('x')[1].replace('G','')) * 1000  # in Mbps
        
        logger.info(f"Configuring test module {module_id} to {module_media_str} {port_config_str}")
        module_configs.append( (module_obj, module_media, port_count, port_speed) )
    await mgmt.set_module_configs(module_configs=module_configs)
    await asyncio.sleep(1.0)
































