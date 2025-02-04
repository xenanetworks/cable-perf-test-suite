################################################################
#
#                   DISABLE AUTOTUNE ON TX TAPS
# 
# This script disables the tx tap auto-tune option on all lanes 
#
# 
################################################################

import asyncio
import sys

from xoa_driver import testers, modules, ports, enums
from xoa_driver.hlfuncs import mgmt
from scripts.libs import *
import logging

#---------------------------
# Global parameters
#---------------------------
CHASSIS_IP = "10.165.136.60"
PORT= "3/0"
USERNAME = "xoa"
AUTOTUNE = False

#---------------------------
# tx_tap_autotune
#---------------------------
async def tx_tap_autotune(chassis_ip: str, username: str, port: str, enable_autotune: bool):

    # configure basic logger
    logger = logging.getLogger("tx_tap_autotune")
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="tx_tap_autotune.log", mode="a"),
            logging.StreamHandler()]
        )
    
    # get module indices and port indices
    _mid_0 = int(port.split("/")[0])
    _pid_0 = int(port.split("/")[1])

    logger.info(f"#####################################################################")
    logger.info(f"Chassis:              {chassis_ip}")
    logger.info(f"Username:             {username}")
    logger.info(f"Port:                 {port}")
    logger.info(f"TX Tap Auto-tune:     {'On' if {enable_autotune} else 'Off'}")
    logger.info(f"#####################################################################")

    # connect to the tester and automatically disconnect when ended
    async with testers.L23Tester(host=chassis_ip, username=username, password="xena", port=22606, enable_logging=False) as tester_obj:
    
        # access module on the tester
        module_obj = tester_obj.modules.obtain(_mid_0)

        # the module must be a freya module
        if not isinstance(module_obj, modules.Z800FreyaModule):
            logger.warning(f"Port {port} is not a Freya port. Abort")
            return None
        
        # get the port object
        port_obj = module_obj.ports.obtain(_pid_0)

        # reserve the port and reset the port
        await mgmt.free_module(module_obj, should_free_ports=True)
        await mgmt.reserve_port(port_obj)
        
        # get number of lanes from the port
        resp = await port_obj.capabilities.get()
        serdes_count = resp.serdes_count

        for i in range(serdes_count):
            if enable_autotune == False:
                logger.info(f"Disable Tx Tap Autotune on Serdes Lane {i}")
                await port_obj.serdes[i].phy.autotune.set_off()
            else:
                logger.info(f"Enable Tx Tap Autotune on Serdes Lane {i}")
                await port_obj.serdes[i].phy.autotune.set_on()
        
        await mgmt.free_port(port_obj)
        

if __name__ == "__main__":
    if len(sys.argv) == 10:
        chassis_ip = sys.argv[1]
        port = sys.argv[2]
        username = sys.argv[3]
        autotune = False if sys.argv[4] == "0" else True
        asyncio.run(tx_tap_autotune(chassis_ip=chassis_ip, username=username, port=port, enable_autotune = autotune))
    elif len(sys.argv) == 1:
        asyncio.run(tx_tap_autotune(chassis_ip=CHASSIS_IP, username=USERNAME, port=PORT, enable_autotune = AUTOTUNE))
    else:
        print.info(f"Not enough parameters")