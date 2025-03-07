# *************************************
# author: leonard.yu@teledyne.com
# *************************************

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