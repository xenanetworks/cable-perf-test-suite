# *************************************
# author: leonard.yu@teledyne.com
# *************************************

from pydantic import BaseModel

class PRBSTestConfig(BaseModel):
    polynomial: str
    duration: int

class PortPair(BaseModel):
    tx: str
    rx: str

class RXOutputEqConfig(BaseModel):
    amp_min: int
    amp_max: int
    pre_min: int
    pre_max: int
    post_min: int
    post_max: int
    delay_after_eq_write: int

class RXOutputEqTestConfig(BaseModel):
    
    port_pair_list: list[PortPair]
    module_media: str
    port_speed: str
    lane: int
    delay_after_reset: int
    prbs_test_config: PRBSTestConfig
    transceiver_eq_config: RXOutputEqConfig

class CablePerformanceTestConfig(BaseModel):
    chassis_ip: str
    username: str
    password: str
    tcp_port: int
    log_filename: str
    rx_output_eq_test_config: RXOutputEqTestConfig