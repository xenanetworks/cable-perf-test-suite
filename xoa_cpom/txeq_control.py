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

@dataclass
class PortTxEqLimits:
    """The port Tx Eq limits 
    """
    def __init__(self, port: FreyaEdunPort, resp: "llicmds.P_CAPABILITIES.GetDataAttr") -> None:
        self.port_obj = port
        self.module_id = port.kind.module_id
        self.port_id = port.kind.port_id
        self.cap_resp = resp
        self.txeq_maxs = self.cap_resp.txeq_max_seq
        self.txeq_mins = self.cap_resp.txeq_min_seq

    @property
    def num_txeq(self) -> int:
        return self.cap_resp.tx_eq_tap_count
    
    @property
    def num_txeq_pre(self) -> int:
        return self.cap_resp.num_txeq_pre
    
    @property
    def num_txeq_post(self) -> int:
        return self.num_txeq - self.num_txeq_pre - 1

    @property
    def txeq_limits(self) -> List[Dict[str, int]]:
        """Return the max and min for each Tx Eq.

        :return: List of dictionaries containing {txeq_index, max, and min}
        :rtype: List[Dict[str, int]]
        """
        limits_dict_list: List[Dict[str, int]] = []
        for i in range(self.num_txeq_pre):
            limits_dict_list.append({
                    "txeq_index": i - self.num_txeq_pre, 
                    "max": self.txeq_maxs[i], 
                    "min": self.txeq_mins[i]
                    })
        limits_dict_list.append({
                "txeq_index": 0, 
                "max": self.txeq_maxs[self.num_txeq_pre], 
                "min": self.txeq_mins[self.num_txeq_pre]
                })
        for j in range(self.num_txeq_post):
            limits_dict_list.append({
                    "txeq_index": j + 1, 
                    "max": self.txeq_maxs[self.num_txeq_pre + 1 + j], 
                    "min": self.txeq_mins[self.num_txeq_pre + 1 + j]
                    })
        return limits_dict_list
    

# *************************************************************************************
# func: read_one_txeq_range_from_lane
# description: Get the TX Eq limits from a lane
# *************************************************************************************
async def read_one_txeq_range_from_lane(port: FreyaEdunPort, lane: int, txeq_index: int, num_txeq_pre: int, num_txeq_post: int, txeq_maxs: List[int], txeq_mins: List[int]) -> Tuple[int, int, int]:
    """Get the TX Eq limits from a lane 

    :param port: Port object
    :type port: FreyaEdunPort
    :param lane: Lane number
    :type lane: int
    :param txeq_index: Tx Eq index. -1 = pre1, -2 = pre2, 0 = main, 1 = post1, 2 = post2
    :type txeq_index: int
    :param num_txeq_pre: Number of Tx pre taps
    :type num_txeq_pre: int
    :param num_txeq_post: Number of Tx post taps
    :type num_txeq_post: int
    :param txeq_maxs: Maximum Tx Eq values
    :type txeq_maxs: List[int]
    :param txeq_mins: Minimum Tx Eq values
    :type txeq_mins: List[int]
    :return: Tuple of current tap value, and its maximum tap value, and minimum tap value
    :rtype: Tuple[int, int, int]
    """
    _serdes_index = lane - 1
    resp = await port.layer1.serdes[_serdes_index].medium.tx.native.get()
    txeqs = resp.tap_values
    
    if txeq_index < 0 and abs(txeq_index) > num_txeq_pre:
        raise ValueError("Invalid TXEQ_PRE tap index")
    if txeq_index > 0 and txeq_index > num_txeq_post:
        raise ValueError("Invalid TXEQ_POST tap index")
    
    _index = 0
    if txeq_index == 0:
        _index = num_txeq_pre
    elif txeq_index < 0:
        _index = num_txeq_pre + txeq_index
    else:
        _index = num_txeq_pre + txeq_index
    return (txeqs[_index], txeq_maxs[_index], txeq_mins[_index])


# *************************************************************************************
# func: read_txeq_from_lanes
# description: Read Tx Eq values from the lanes.
# *************************************************************************************
async def read_txeq_from_lanes(port: FreyaEdunPort, lanes: List[int]) -> List[Dict[str, Any]]:
    """Read host tx eq values of the lanes

    :param port: Port object
    :type port: FreyaEdunPort
    :param lanes: List of lanes to read tx eq values
    :type lanes: List[int]
    :return: List of dictionaries, each containing a lane number and its corresponding tx eq values. 
    :rtype: List[Dict[str, Any]]
    """
    cmd_list = []
    for lane in lanes:
        _serdes_index = lane - 1
        cmd_list.append(
            port.layer1.serdes[_serdes_index].medium.tx.native.get()
        )

    resps = await utils.apply(*cmd_list)
    results = []
    for lane, resp in zip(lanes, resps):
        results.append({"lane": lane, "txeq_values": resp.tap_values})
    await asyncio.sleep(1)
    return results

# *************************************************************************************
# func: optimize_txeq_on_lanes
# description: Update one TX eq value from the lanes. 
# *************************************************************************************
async def optimize_txeq_on_lanes(port: FreyaEdunPort, lanes: List[int], txeq_index: int, mode: str, delay_after_write: int, logger_name: str, port_txeq_limits: PortTxEqLimits) -> List[int]:
    """Update one Tx eq on the lanes

    :param port: Port object
    :type port: FreyaEdunPort
    :param lanes: List of lanes to update tx eq values
    :type lanes: List[int]
    :param txeq_index: Tx eq index. -1 = pre1, -2 = pre2, 0 = main, 1 = post1, 2 = post2
    :type txeq_index: int
    :param mode: Mode to update the eq value, "inc" for increase the absolute value, "dec" for decrease the absolute value. 
    
    For pre and post eq (txeq_index of -1 and 1), "inc" means decrease the negative value (e.g.,-2 to -3), "dec" means increase the negative value (e.g., -3 to -2). 

    :type mode: str
    :param delay_after_write: Delay time after writing the tx eq values
    :type delay_after_write: int
    :param logger_name: Logger name
    :type logger_name: str
    :param port_txeq_limits: PortTxEqLimits object containing the port's tx eq limits
    :type port_txeq_limits: PortTxEqLimits
    :return: List of lanes that have been updated successfully. An empty list means no lane has been updated.
    :rtype: List[int]
    """
    num_txeq_pre = 0
    num_txeq_post = 0
    eq_max = 0
    eq_min = 0
    for limit in port_txeq_limits.txeq_limits:
        if limit["txeq_index"] == txeq_index:
            num_txeq_pre = port_txeq_limits.num_txeq_pre
            num_txeq_post = port_txeq_limits.num_txeq_post
            eq_max = limit["max"]
            eq_min = limit["min"]
            break

    if txeq_index < 0 and abs(txeq_index) > num_txeq_pre:
        raise ValueError("Invalid TXEQ_PRE index")
    if txeq_index > 0 and txeq_index > num_txeq_post:
        raise ValueError("Invalid TXEQ_POST index")
    
    max_txeq_sum = 87 if isinstance(port, ports.Z800FreyaPort) else 168

    # Read the current TxEq values from the lanes
    cmd_list = []
    for lane in lanes:
        serdes_index = lane - 1
        cmd_list.append(
            port.layer1.serdes[serdes_index].medium.tx.native.get()
        )
    resps = await utils.apply(*cmd_list)
    lane_txeq_dicts = []
    for lane, resp in zip(lanes, resps):  
        lane_txeq_dicts.append({"lane": lane, "txeq_values": resp.tap_values})

    # On each lane, update the specified TxEq value based on the mode, if within limits
    results = []
    for lane_txeq_dict in lane_txeq_dicts:
        lane = lane_txeq_dict["lane"]
        txeqs = lane_txeq_dict["txeq_values"]
        txeq_sum = sum(abs(i) for i in txeqs)
        
        if txeq_sum >= max_txeq_sum:
            continue
        
        # prepare the txeq index 
        _index = 0
        if txeq_index == 0:
            _index = num_txeq_pre
        elif txeq_index < 0:
            _index = num_txeq_pre + txeq_index
        else:
            _index = num_txeq_pre + txeq_index

        serdes_index = lane - 1
        if mode == "inc":
            if txeq_index == -1 or txeq_index == 1:
                if txeqs[_index] <= eq_min:
                    continue
                else:
                    txeqs[_index] -= 1
                    await port.layer1.serdes[serdes_index].medium.tx.native.set(tap_values=txeqs)
                    results.append(lane)
            else:
                if txeqs[_index] >= eq_max:
                    continue
                else:
                    txeqs[_index] += 1
                    await port.layer1.serdes[serdes_index].medium.tx.native.set(tap_values=txeqs)
                    results.append(lane)
        elif mode == "dec":
            if txeq_index == -1 or txeq_index == 1:
                if txeqs[_index] >= eq_max:
                    continue
                else:
                    txeqs[_index] += 1
                    await port.layer1.serdes[serdes_index].medium.tx.native.set(tap_values=txeqs)
                    results.append(lane)
            else:
                if txeqs[_index] <= eq_min:
                    continue
                else:
                    txeqs[_index] -= 1
                    await port.layer1.serdes[serdes_index].medium.tx.native.set(tap_values=txeqs)
                    results.append(lane)

    # Wait for a certain duration to let the EQ settings take effect.
    logger = logging.getLogger(logger_name)
    logger.info(f"Delay after EQ write: {delay_after_write}s")
    await asyncio.sleep(delay_after_write)
    return results


# *************************************************************************************
# func: write_txeq_to_lanes
# description: Load Tx tap values to the lanes.
# *************************************************************************************
async def write_txeq_to_lanes(port: FreyaEdunPort, lane_txeq_list: List[Tuple[int, List[int]]], delay_after_write: int, logger_name: str) -> None:
    """Write Tx eq values to the lanes

    :param port: Port object
    :type port: FreyaEdunPort
    :param lane_txeq_list: List of (lane index, txeq values), each containing a lane number and its corresponding Tx eq values. The order of eq values must be from the lowest index to highest index, e.g., [pre2, pre1, main, post1, post2]
    :type lane_txeq_list: List[Tuple[int, List[int]]]
    :param logger_name: Logger name
    :type logger_name: str
    """
    # Get logger
    logger = logging.getLogger(logger_name)
    cmd_list = []
    for _lane, _txeq_values in lane_txeq_list:
        _serdes_index = _lane - 1
        cmd_list.append(
            port.layer1.serdes[_serdes_index].medium.tx.native.set(tap_values=_txeq_values)
        )
        logger.info(f"Port {port.kind.module_id}/{port.kind.port_id}: Write tx eq values {_txeq_values} to Lane {_lane}")
    await utils.apply(*cmd_list)
    logger.info(f"Delay after EQ write: {delay_after_write}s")
    await asyncio.sleep(delay_after_write)


# *************************************************************************************
# func: get_port_txeq_limits
# description: Get the Tx Eq limits from the port
# *************************************************************************************
async def get_port_txeq_limits(port: FreyaEdunPort) -> PortTxEqLimits:
    """Get the Tx Eq limits from the port

    :param port: Port object
    :type port: FreyaEdunPort
    :return: Tuple of maximum Tx Eq values and minimum Tx Eq values
    :rtype: Tuple[int, int, int, List[int], List[int]]
    """
    resp = await port.capabilities.get()
    result = PortTxEqLimits(port=port, resp=resp)
    return result

