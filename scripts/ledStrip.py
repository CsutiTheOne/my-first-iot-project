#!/usr/bin/env python3
"""
LED Strip Controller

Controls a Bluetooth Low Energy (BLE) LED strip to turn on, turn off, or run a gradual
sunrise alarm effect (dimming up with color gradient from faint red -> mid yellow -> bright white).

Usage Examples:
    # Positional syntax:
    python scripts/ledStrip.py on BE:60:09:00:02:27
    python scripts/ledStrip.py off BE:60:09:00:02:27
    python scripts/ledStrip.py sunrise 30 BE:60:09:00:02:27
    python scripts/ledStrip.py sunrise BE:60:09:00:02:27         # Default: 30 minutes
    python scripts/ledStrip.py BE:60:09:00:02:27 on

    # Named / flag syntax:
    python scripts/ledStrip.py -a BE:60:09:00:02:27 -m on
    python scripts/ledStrip.py -a BE:60:09:00:02:27 -m off
    python scripts/ledStrip.py -a BE:60:09:00:02:27 -m sunrise -d 30
"""

import argparse
import asyncio
import sys
from bleak import BleakClient, BleakScanner

UUID = "0000fff3-0000-1000-8000-00805f9b34fb"

POWER_ON = bytes.fromhex("7e 07 04 ff 00 01 02 01 ef")
POWER_OFF = bytes.fromhex("7e 07 04 00 00 00 02 01 ef")


def make_color_packet(r: int, g: int, b: int) -> bytes:
    """Generate GATT command packet for RGB color (0-255)."""
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return bytes([0x7E, 0x07, 0x05, 0x03, r, g, b, 0x10, 0xEF])


def make_brightness_packet(value: int) -> bytes:
    """Generate GATT command packet for brightness (1-100)."""
    value = max(1, min(100, int(value)))
    return bytes([0x7E, 0x04, 0x01, value, 0x01, 0xFF, 0x02, 0x01, 0xEF])


async def turn_on(client: BleakClient) -> None:
    """Turn the LED strip on."""
    await client.write_gatt_char(UUID, POWER_ON, response=False)
    await asyncio.sleep(0.1)
    print("Turned on")


async def turn_off(client: BleakClient) -> None:
    """Turn the LED strip off."""
    await client.write_gatt_char(UUID, POWER_OFF, response=False)
    await asyncio.sleep(0.1)
    print("Turned off")


async def run_sunrise(client: BleakClient, duration_minutes: float) -> None:
    """
    Gradually dim up the LED strip over `duration_minutes` (default 30),
    transitioning from faint red -> mid yellow -> bright white.
    """
    total_seconds = duration_minutes * 60.0
    steps = min(200, max(10, int(total_seconds / 0.2)))
    interval = total_seconds / steps

    print(
        f"Starting sunrise effect: duration {duration_minutes:.1f}m "
        f"({steps} steps, ~{interval:.1f}s interval)..."
    )

    # Preparation: Turn off, set faint red & minimum brightness, then power on
    await client.write_gatt_char(UUID, POWER_OFF, response=False)
    await asyncio.sleep(0.1)

    await client.write_gatt_char(UUID, make_color_packet(255, 0, 0), response=False)
    await asyncio.sleep(0.1)

    await client.write_gatt_char(UUID, make_brightness_packet(1), response=False)
    await asyncio.sleep(0.1)

    await client.write_gatt_char(UUID, POWER_ON, response=False)

    # Gradually increase brightness and adjust color:
    # 0%   -> faint red (255, 0, 0)
    # 50%  -> mid yellow (255, 255, 0)
    # 100% -> bright white (255, 255, 255)
    for step in range(1, steps + 1):
        await asyncio.sleep(interval)
        progress = step / steps

        # Brightness smoothly scales from 1 to 100
        brightness_val = int(round(1 + 99 * progress))

        # First half (progress 0.0 -> 0.5): Red -> Yellow (increase Green)
        # Second half (progress 0.5 -> 1.0): Yellow -> White (increase Blue)
        r = 255
        g = int(round(255 * min(1.0, progress * 2)))
        b = int(round(255 * max(0.0, (progress - 0.5) * 2)))

        await client.write_gatt_char(
            UUID, make_brightness_packet(brightness_val), response=False
        )
        await client.write_gatt_char(
            UUID, make_color_packet(r, g, b), response=False
        )

    print("Sunrise complete")


def parse_arguments(argv: list[str]) -> tuple[str, str, float]:
    """
    Parse command-line arguments supporting both positional and named flag styles.

    Returns:
        (command, address, duration_minutes)
    """
    parser = argparse.ArgumentParser(
        description="BLE LED Strip Controller (on, off, sunrise).",
        epilog=(
            "Examples:\n"
            "  %(prog)s on BE:60:09:00:02:27\n"
            "  %(prog)s off BE:60:09:00:02:27\n"
            "  %(prog)s sunrise 30 BE:60:09:00:02:27\n"
            "  %(prog)s sunrise BE:60:09:00:02:27\n"
            "  %(prog)s -a BE:60:09:00:02:27 -m sunrise -d 15\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-a",
        "--address",
        dest="flag_address",
        metavar="ADDRESS",
        help="BLE MAC address of the controller",
    )
    parser.add_argument(
        "-m",
        "--mode",
        dest="flag_mode",
        metavar="MODE",
        choices=["on", "off", "sunrise"],
        help="Operation to execute: on, off, sunrise",
    )
    parser.add_argument(
        "-d",
        "--duration",
        dest="flag_duration",
        metavar="MINUTES",
        type=float,
        help="Sunrise duration in minutes (default: 30)",
    )
    parser.add_argument(
        "positional",
        nargs="*",
        help="Positional arguments: [command] [address] [duration] in any order",
    )

    args = parser.parse_args(argv)

    command = args.flag_mode
    address = args.flag_address
    duration = args.flag_duration

    for token in args.positional:
        low = token.lower()
        if low in ("on", "off", "sunrise"):
            if command is None:
                command = low
            else:
                parser.error(f"Conflicting command specified: {command} vs {token}")
        else:
            try:
                val = float(token)
                if duration is None:
                    duration = val
                else:
                    parser.error(f"Conflicting duration specified: {duration} vs {token}")
            except ValueError:
                if address is None:
                    address = token
                else:
                    parser.error(f"Conflicting address specified: {address} vs {token}")

    if command is None:
        parser.error("Operation required: 'on', 'off', or 'sunrise'.")

    if address is None:
        parser.error("BLE device address is required.")

    if duration is None:
        duration = 30.0
    elif duration <= 0:
        parser.error("Duration must be a positive number greater than 0.")

    return command, address, duration


async def main() -> None:
    command, address, duration = parse_arguments(sys.argv[1:])

    print(f"Scanning for BLE device {address} (timeout 15s)...")
    device = await BleakScanner.find_device_by_address(address, timeout=15)
    if device is None:
        raise RuntimeError(f"LED controller with address '{address}' not found.")

    async with BleakClient(device) as client:
        if command == "on":
            await turn_on(client)
        elif command == "off":
            await turn_off(client)
        elif command == "sunrise":
            await run_sunrise(client, duration)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(130)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
