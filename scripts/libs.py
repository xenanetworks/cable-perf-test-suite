# ***********************************************************************************************
# this library file contains functions for dp init, register rw, prbs ber read, etc.
# ***********************************************************************************************

import asyncio

from xoa_driver import testers, modules, ports, enums
from xoa_driver.misc import Hex
from xoa_driver.hlfuncs import mgmt
from enums import *
import logging
import math
from typing_extensions import List, Any

# *************************************************************************************
# func: stop_auto_dp_init
# description: Stop Auto Data Path Init of the Module (Write address 128 value 0xFF)
# *************************************************************************************
async def stop_auto_dp_init(port: ports.Z800FreyaPort, logger_name: str):
    """Stop Auto Data Path Init of the Module (Write address 128 value 0xFF)
    """
    # Get logger
    logger = logging.getLogger(logger_name)
    logger.info(f"Port {port.kind.module_id}/{port.kind.port_id}: Stop Auto Data Path Init of the Module (Write address 128 value 0xFF)")
    await port.transceiver.access_rw_seq(page_address=0x10, register_address=128, byte_count=1).set(value=Hex("FF"))
    await asyncio.sleep(1)

# *************************************************************************************
# func: apply_dp_init
# description: Apply Data Path Init (Write address 143 value 0xFF)
# *************************************************************************************
async def apply_dp_init(port: ports.Z800FreyaPort, logger_name: str):
    """Apply Data Path Init (Write address 143 value 0xFF)
    """
    # Get logger
    logger = logging.getLogger(logger_name)
    logger.info(f"Port {port.kind.module_id}/{port.kind.port_id}: Apply Data Path Init (Write address 143 value 0xFF)")
    await port.transceiver.access_rw_seq(page_address=0x10, register_address=143, byte_count=1).set(value=Hex("FF"))
    await asyncio.sleep(1)

# *************************************************************************************
# func: activate_dp
# description: Activate Data Path (Write address 128 with value 0x00)
# *************************************************************************************
async def activate_dp(port: ports.Z800FreyaPort, logger_name: str):
    """Activate Data Path (Write address 128 with value 0x00)
    """
    # Get logger
    logger = logging.getLogger(logger_name)
    logger.info(f"Port {port.kind.module_id}/{port.kind.port_id}: Activate Data Path (Write address 128 with value 0x00)")
    await port.transceiver.access_rw_seq(page_address=0x10, register_address=128, byte_count=1).set(value=Hex("00"))
    await asyncio.sleep(1)

# *************************************************************************************
# func: output_eq_write
# description: Write input dB value to a specified cursor on a specified lane
# *************************************************************************************
async def output_eq_write(port: ports.Z800FreyaPort, lane: int, db: int, cursor: Cursor, logger_name: str):
    """Write input dB value to a specified cursor on a specified lane
    """
    # Get logger
    logger = logging.getLogger(logger_name)
    logger.info(f"Port {port.kind.module_id}/{port.kind.port_id}: Write {db} dB to {cursor.name} - Lane {lane} ")
    assert 1<=lane<=8
    assert 0<=db<=7

    _start_addr = 161
    # find byte address based on lane index and Pre/Post/Amplitude
    _reg_addr = _start_addr + int(cursor.value*4) + math.ceil(lane/2)
    
    _is_upper_lane = False
    if lane % 2 == 0: # upper lane, value should update bit 7-4
        _is_upper_lane = True

    # read the byte from the address
    resp = await port.transceiver.access_rw_seq(page_address=0x10, register_address=_reg_addr, byte_count=1).get()
    await asyncio.sleep(1)
    _tmp = int(resp.value, 16) # convert the existing byte value from hex string to int
    
    if _is_upper_lane: # upper lane, value should update bit 7-4
        _value = db << 4 # move the value 4 bits to the left
        _tmp &= 0x0F # erase bit 7-4
        _tmp |= _value # add the desired value
    else: # lower lane, value should update bit 3-0
        _value = db # the value as is
        _tmp &= 0xF0 # erase bit 3-0
        _tmp |= _value # add the desired value
    
    # write the new byte into the address
    await port.transceiver.access_rw_seq(page_address=0x10, register_address=_reg_addr, byte_count=1).set(value=Hex('{:02X}'.format(_tmp)))
    await asyncio.sleep(1)

    # read the byte from the address again to verify the write
    resp = await port.transceiver.access_rw_seq(page_address=0x10, register_address=_reg_addr, byte_count=1).get()
    await asyncio.sleep(1)
    _tmp = int(resp.value, 16) # convert the existing byte value from hex string to int
    if _is_upper_lane:
        _tmp &= 0xF0 # take the bit 7-4 of the read
        _read = _tmp >> 4
    else:
        _tmp &= 0x0F # take the bit 7-4 of the read
        _read = _tmp
    if _read == db:
        logger.info(f"  Write operation successful")
    else:
        logger.info(f"  Write operation failed. (Wrote {db} dB but read {_read})")

# *************************************************************************************
# func: output_eq_read
# description: Read dB value from a specified cursor on a specified lane
# *************************************************************************************
async def output_eq_read(port: ports.Z800FreyaPort, lane: int, cursor: Cursor, logger_name: str):
    """Read dB value from a specified cursor on a specified lane
    """
    # Get logger
    logger = logging.getLogger(logger_name)

    assert 1<=lane<=8

    _start_addr = 161
    # find byte address based on lane index and Pre/Post/Amplitude
    _reg_addr = _start_addr + int(cursor.value*4) + math.ceil(lane/2)
    
    _is_upper_lane = False
    if lane % 2 == 0: # upper lane, value should update bit 7-4
        _is_upper_lane = True

    # read the byte from the address
    resp = await port.transceiver.access_rw_seq(page_address=0x10, register_address=_reg_addr, byte_count=1).get()
    await asyncio.sleep(1)
    _tmp = int(resp.value, 16) # convert the existing byte value from hex string to int
    if _is_upper_lane:
        _tmp &= 0xF0 # take the bit 7-4 of the read
        _read = _tmp >> 4
    else:
        _tmp &= 0x0F # take the bit 7-4 of the read
        _read = _tmp
    logger.info(f"Port {port.kind.module_id}/{port.kind.port_id}: Read {_read} dB from {cursor.name} - Lane {lane} ")

# *************************************************************************************
# func: app_sel
# description: Write AppSelCode, DataPathID, and ExplicitControl to a specified lane
# *************************************************************************************
async def app_sel(port: ports.Z800FreyaPort, lane: int, appsel_code: int, dp_id: int, explicit_ctrl: int, logger_name: str):
    """Write AppSelCode, DataPathID, and ExplicitControl to a specified lane
    """
    # Get logger
    logger = logging.getLogger(logger_name)
    logger.info(f"Port {port.kind.module_id}/{port.kind.port_id}: Write AppSelCode={appsel_code}, DataPathID={dp_id}, ExplicitControl={explicit_ctrl} - Lane {lane} ")
    assert 1<=lane<=8
    assert 0<=appsel_code<=15
    assert 0<=dp_id<=7
    assert 0<=explicit_ctrl<=1

    # find byte address based on lane index and Pre/Post/Amplitude
    _reg_addr = 144 + lane
    _tmp = (appsel_code<<4) + (dp_id<<1) + explicit_ctrl
    
    # write the new byte into the address
    await port.transceiver.access_rw_seq(page_address=0x10, register_address=_reg_addr, byte_count=1).set(value=Hex('{:02X}'.format(_tmp)))
    await asyncio.sleep(1)

    # read the byte from the address again to verify the write
    resp = await port.transceiver.access_rw_seq(page_address=0x10, register_address=_reg_addr, byte_count=1).get()
    await asyncio.sleep(1)
    _tmp2 = int(resp.value, 16) # convert the existing byte value from hex string to int
    if _tmp2 == _tmp:
        logger.info(f"  Write operation successful")
    else:
        logger.info(f"  Write operation failed. (Wrote 0x{_tmp} but read 0x{_tmp2})")

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



def get_port_list(tester_obj: testers.L23Tester, port_pair_list: List[dict], key_str: str) -> List[Any]:
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

async def reserve_reset_ports_in_list(tester_obj: testers.L23Tester, port_obj_list: List[ports.Z800FreyaPort]) -> None:
    for _port in port_obj_list:
        _module_id = _port.kind.module_id
        _module = tester_obj.modules.obtain(_module_id)
        await mgmt.free_module(module=_module, should_free_ports=False)
        await mgmt.reserve_port(_port)
        await mgmt.reset_port(_port)
    await asyncio.sleep(1.0)

async def release_ports_in_list(port_obj_list: List[ports.Z800FreyaPort]) -> None:
    for _port in port_obj_list:
        await mgmt.free_port(_port)
    await asyncio.sleep(1.0)