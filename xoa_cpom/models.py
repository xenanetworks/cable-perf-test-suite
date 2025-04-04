# *************************************
# author: leonard.yu@teledyne.com
# *************************************

from pydantic import BaseModel
from typing import (
    Generator,
    Dict,
    List,
    Optional,
    Any
)

class PRBSTestConfig(BaseModel):
    polynomial: str
    duration: int

class PortPair(BaseModel):
    tx: str
    rx: str

class RXOutputEqRange(BaseModel):
    amp_min: int
    amp_max: int
    pre_min: int
    pre_max: int
    post_min: int
    post_max: int

class RXOutputEqTestConfig(BaseModel):
    module_list: list[int]
    port_pair_list: list[PortPair]
    module_media: str
    port_speed: str
    lane: int
    delay_after_reset: int
    prbs_config: PRBSTestConfig
    rx_output_eq_range: RXOutputEqRange
    delay_after_eq_write: int

class TxInputEqRange(BaseModel):
    min: int
    max: int

class TxInputEqTestConfig(BaseModel):
    module_list: list[int]
    port_pair_list: list[PortPair]
    module_media: str
    port_speed: str
    lane: int
    delay_after_reset: int    
    prbs_config: PRBSTestConfig
    tx_input_eq_range: TxInputEqRange
    delay_after_eq_write: int

class CablePerformanceTestConfig(BaseModel):
    chassis_ip: str
    username: str
    password: Optional[str] = None
    tcp_port: Optional[int] = None
    log_filename: Optional[str] = None
    
    rx_output_eq_test_config: Optional[RXOutputEqTestConfig] = None
    tx_input_eq_test_config: Optional[TxInputEqTestConfig] = None