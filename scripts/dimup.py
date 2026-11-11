import asyncio
from bleak import BleakClient, BleakScanner

MAC = "BE:60:09:00:02:27"  # Replace with your controller's address

UUID = "0000fff3-0000-1000-8000-00805f9b34fb"

DURATION = 30 * 60  # 30 minutes
STEPS = 200

r = 255
g = 0
b = -255

G_STEP = 255 / (STEPS / 2)
B_STEP = 255 * 2 / STEPS

POWER_ON = bytes.fromhex("7e 07 04 ff 00 01 02 01 ef")
POWER_OFF = bytes.fromhex("7e 07 04 00 00 00 02 01 ef")


def color(r, g, b):
    return bytes([0x7e, 0x07, 0x05, 0x03,
                  r, g, b, 0x10, 0xef])


def brightness(value):
    value = max(1, min(100, value))
    return bytes([0x7e, 0x04, 0x01, value,
                  0x01, 0xff, 0x02, 0x01, 0xef])


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
        global r, g, b

        # Prepare the LED strip
        await send(POWER_OFF)
        await asyncio.sleep(0.1)

        await send(color(r, 0, 0))  
        await asyncio.sleep(0.1)

        await send(brightness(1))
        await asyncio.sleep(0.1)

        await send(POWER_ON)

        # Gradually increase brightness
        for level in range(2, STEPS + 1):
            await asyncio.sleep(DURATION / (STEPS - 1))
            g = int(min(255, g + G_STEP))
            b = int(min(255, b + B_STEP))
            await send(brightness(level))
            await send(color(r, g, max(0, b)))  
        print("Sunrise complete")


if __name__ == "__main__":
    asyncio.run(main())
