import asyncio

from xoa_driver import testers, modules, ports, enums
from xoa_driver.hlfuncs import mgmt, anlt
from xoa_driver.lli import commands
from xoa_driver.misc import Hex
from type import *
from enums import *

from typing import Generator, Optional, Union, List, Dict, Any, Tuple
import logging
from contextlib import suppress
import math

async def stop_auto_dp_init(port: ports.GenericL23Port, logger: logging.Logger):
    print(f"Port {port.kind.module_id}/{port.kind.port_id}: Stop Auto Data Path Init of the Module (Write address 128 value 0xFF)")
    await port.transceiver.access_rw_seq(page_address=0x10, register_address=128, byte_count=1).set(value=Hex("FF"))

async def apply_dp_init(port: ports.GenericL23Port, logger: logging.Logger):
    print(f"Port {port.kind.module_id}/{port.kind.port_id}: Apply Data Path Init (Write address 143 value 0xFF)")
    await port.transceiver.access_rw_seq(page_address=0x10, register_address=143, byte_count=1).set(value=Hex("FF"))

async def activate_dp(port: ports.GenericL23Port, logger: logging.Logger):
    print(f"Port {port.kind.module_id}/{port.kind.port_id}: Activate Data Path (Write address 128 with value 0x00)")
    await port.transceiver.access_rw_seq(page_address=0x10, register_address=128, byte_count=1).set(value=Hex("00"))

async def output_eq_write(port: ports.GenericL23Port, lane: int, db: int, cursor: Cursor, logger: logging.Logger):
    print(f"Port {port.kind.module_id}/{port.kind.port_id}: Write {db} dB to {cursor.name} - Lane {lane} ")
    assert 1<=lane<=8
    assert 0<=db<=7

    # find byte address based on lane index and Pre/Post/Amplitude
    _reg_addr = math.ceil(lane/2) + 161 + int(cursor.value*4)
    
    _is_upper_lane = False
    if lane % 2 == 0: # upper lane, value should update bit 7-4
        _is_upper_lane = True

    # read the byte from the address
    resp = await port.transceiver.access_rw_seq(page_address=0x10, register_address=_reg_addr, byte_count=1).get()
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

    # read the byte from the address again to verify the write
    resp = await port.transceiver.access_rw_seq(page_address=0x10, register_address=_reg_addr, byte_count=1).get()
    _tmp = int(resp.value, 16) # convert the existing byte value from hex string to int
    if _is_upper_lane:
        _tmp &= 0xF0 # take the bit 7-4 of the read
        _read = _tmp >> 4
    else:
        _tmp &= 0x0F # take the bit 7-4 of the read
        _read = _tmp
    if _read == db:
        print(f"  Write operation successful")
    else:
        print(f"  Write operation failed. (Wrote {db} dB but read {_read})")

async def app_sel(port: ports.GenericL23Port, lane: int, appsel_code: int, dp_id: int, explicit_ctrl: int, logger: logging.Logger):
    print(f"Port {port.kind.module_id}/{port.kind.port_id}: Write AppSelCode={appsel_code}, DataPathID={dp_id}, ExplicitControl={explicit_ctrl} - Lane {lane} ")
    assert 1<=lane<=8
    assert 0<=appsel_code<=15
    assert 0<=dp_id<=7
    assert 0<=explicit_ctrl<=1

    # find byte address based on lane index and Pre/Post/Amplitude
    _reg_addr = 144 + lane
    _tmp = (appsel_code<<4) + (dp_id<<1) + explicit_ctrl
    
    # write the new byte into the address
    await port.transceiver.access_rw_seq(page_address=0x10, register_address=_reg_addr, byte_count=1).set(value=Hex('{:02X}'.format(_tmp)))

    # read the byte from the address again to verify the write
    resp = await port.transceiver.access_rw_seq(page_address=0x10, register_address=_reg_addr, byte_count=1).get()
    _tmp2 = int(resp.value, 16) # convert the existing byte value from hex string to int
    if _tmp2 == _tmp:
        print(f"  Write operation successful")
    else:
        print(f"  Write operation failed. (Wrote 0x{_tmp} but read 0x{_tmp2})")

async def read_prbs_ber(port: ports.GenericL23Port, lane: int, logger: logging.Logger) -> float:
    assert 1<=lane<=8
    # read starting PRBS BER
    _prbs_ber = 0.0
    _serdes = lane - 1
    resp = await port.serdes[_serdes].prbs.status.get()
    _prbs_bits = resp.byte_count * 8
    _prbs_errors = resp.error_count
    if _prbs_errors == 0:
        _prbs_ber = 4.6/_prbs_bits
        print(f"PRBS BER [{lane}]: < {'{0:.3e}'.format(_prbs_ber)}")
    else:
        _prbs_ber = _prbs_errors/_prbs_bits
        print(f"PRBS BER [{lane}]: {'{0:.3e}'.format(_prbs_ber)}")
    return _prbs_ber
    
def less_equal(current: float, target:float) -> bool:
    if current <= target:
        return True
    else:
        return False
    