# ***********************************************************************************************
# this library file contains test configuration models for cable quality test
# ***********************************************************************************************

from pydantic import BaseModel

class PRBSTestConfig(BaseModel):
    polynomial: str
    duration: int

class PortPair(BaseModel):
    tx: str
    rx: str

class TransceiverEQConfig(BaseModel):
    amp_min: int
    amp_max: int
    pre_min: int
    pre_max: int
    post_min: int
    post_max: int
    delay_after_eq_write: int

class CablePerfOptimalTestConfig(BaseModel):
    chassis_ip: str
    username: str
    password: str
    tcp_port: int
    log_filename: str
    port_pair_list: list[PortPair]
    module_media: str
    port_speed: str
    lane: int
    delay_after_reset: int
    prbs_test_config: PRBSTestConfig
    transceiver_eq_config: TransceiverEQConfig

class TransceiverInitConfig(BaseModel):
    amp_init: int
    pre_init: int
    post_init: int
    target_prbs_ber: float
    delay_after_eq_write: int

class CablePerfTargetTestConfig(BaseModel):
    chassis_ip: str
    username: str
    password: str
    tcp_port: int
    log_filename: str
    port_pair_list: list[PortPair]
    module_media: str
    port_speed: str
    lane: int
    delay_after_reset: int
    prbs_test_config: PRBSTestConfig
    transceiver_init_config: TransceiverInitConfig