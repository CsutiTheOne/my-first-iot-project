import asyncio
from bleak import BleakClient, BleakScanner

MAC = "BE:60:09:00:02:27"  # Replace with your controller's address

UUID = "0000fff3-0000-1000-8000-00805f9b34fb"

POWER_ON = bytes.fromhex("7e 07 04 ff 00 01 02 01 ef")
POWER_OFF = bytes.fromhex("7e 07 04 00 00 00 02 01 ef")



async def main():
    device = await BleakScanner.find_device_by_address(
        MAC, timeout=15
    )

    if device is None:
        raise RuntimeError("LED controller not found")

    async with BleakClient(device) as client:

        async def send(command):
            await client.write_gatt_char(
                UUID, command, response=False
            )

        # Prepare the LED strip
        await send(POWER_OFF)
        await asyncio.sleep(0.1)


        print("Turned off")


if __name__ == "__main__":
    asyncio.run(main())
