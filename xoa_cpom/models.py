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

class TcvrRxOutputEqRange(BaseModel):
    amp_min: int
    amp_max: int
    pre_min: int
    pre_max: int
    post_min: int
    post_max: int

class TcvrTxInputEqRange(BaseModel):
    min: int
    max: int

class HostTxEqPreset(BaseModel):
    pre3: int
    pre2: int
    pre1: int
    main: int
    post1: int
    post2: int

class TcvrRxOutputEqTestConfig(BaseModel):
    module_list: list[int]
    port_pair_list: list[PortPair]
    module_media: str
    port_speed: str
    lane: int
    delay_after_reset: int
    prbs_config: PRBSTestConfig
    rx_output_eq_range: TcvrRxOutputEqRange
    delay_after_eq_write: int

class TcvrTxInputEqTestConfig(BaseModel):
    module_list: list[int]
    port_pair_list: list[PortPair]
    module_media: str
    port_speed: str
    lane: int
    delay_after_reset: int    
    prbs_config: PRBSTestConfig
    tx_input_eq_range: TcvrTxInputEqRange
    delay_after_eq_write: int

class HostTxEqTestConfig(BaseModel):
    module_list: list[int]
    port_pair_list: list[PortPair]
    module_media: str
    port_speed: str
    lane: int
    delay_after_reset: int
    prbs_config: PRBSTestConfig
    delay_after_eq_write: int
    target_ber: float
    preset_tap_values: HostTxEqPreset
    search_mode: str  # "heuristic" or "exhaustive"
    search_taps: List[int]

class CablePerformanceTestConfig(BaseModel):
    chassis_ip: str
    username: str
    password: Optional[str] = None
    tcp_port: Optional[int] = None
    log_filename: Optional[str] = None
    csv_report_filename: str
    tcvr_rx_output_eq_test_config: Optional[TcvrRxOutputEqTestConfig] = None
    tcvr_tx_input_eq_test_config: Optional[TcvrTxInputEqTestConfig] = None
    host_tx_eq_test_config: Optional[HostTxEqTestConfig] = None