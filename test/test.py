# *************************************
# author: leonard.yu@teledyne.com
# *************************************
import sys
import os
currentdir = os.path.dirname(os.path.abspath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(currentdir)
sys.path.append(parentdir)

import asyncio
from xoa_cpom.cpom import XenaCablePerfOptimization

async def main():
    stop_event = asyncio.Event()
    try:
        test = XenaCablePerfOptimization("test_config.yml")
        await test.connect()
        await test.rx_output_eq_optimization_test.run()
        await test.disconnect()
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    asyncio.run(main())