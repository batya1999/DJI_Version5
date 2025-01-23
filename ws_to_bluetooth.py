from typing import Optional

import websocket
import argparse
import asyncio
import struct
from bleak import BleakScanner, BleakClient

# Define the format of the struct: 6 int16_t values
STRUCT_FORMAT = "<4h"  # Little-endian (<), 6 short integers (h)  # TODO change to 6h

DEVICE_NAME = "DJI_REMOTE_TRPY"  # The advertised BLE name
SERVICE_UUID = "1fbcdfb1-8e73-4296-9057-a6ee3133902a"
CHARACTERISTIC_UUID = "d97e4ec1-d3c4-4952-a421-884719fe35f7"


async def find_ble_device() -> Optional[BleakClient]:
    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover(timeout=5.0)

    if not devices:
        print("No devices found. Ensure BLE is enabled and the target device is advertising.")
        return None

    print("\nDiscovered devices:")
    for d in devices:
        print(f"Name: {d.name}, Address: {d.address}")

    # Look for the device by name
    target_device = next((d for d in devices if d.name == DEVICE_NAME), None)

    if not target_device:
        print(f"\nDevice '{DEVICE_NAME}' not found. Check your device is advertising.")
        return None

    print(f"\nFound {DEVICE_NAME} at address {target_device.address}. Connecting...")
    return BleakClient(target_device.address)


def parse_message(message):
    try:
        if message.startswith("moveDrone:"):
            values = message[len("moveDrone:"):].split(',')
        else:
            values = message.split(',')
        if len(values) == 4:
            roll, pitch, yaw, throttle = map(float, values)
            print(f'Received: {roll=}, {pitch=}, {yaw=}, {throttle=}')
            return int(roll), int(pitch), int(yaw), int(throttle)
        elif len(values) == 6:
            roll, pitch, yaw, throttle, camera, command = map(float, values)
            print(f'Received: {roll=}, {pitch=}, {yaw=}, {throttle=}, {camera=}, {command=} (only sending first 4)')
            return int(roll), int(pitch), int(yaw), int(throttle)
    except ValueError:
        raise ValueError("Invalid message format")


async def connect_and_reroute(ble_client, server_url):
    """Handles sending data to the BLE device."""
    try:
        await ble_client.connect()

        if ble_client.is_connected:
            print(f"Connected to {DEVICE_NAME}!")

            async def forward_to_ble(ws, msg):
                print(f"Received message: {msg}")
                roll, pitch, yaw, throttle = parse_message(msg)
                data = struct.pack(STRUCT_FORMAT, throttle, yaw, pitch, roll)
                print("Sending data:", [throttle, yaw, pitch, roll])
                await ble_client.write_gatt_char(CHARACTERISTIC_UUID, data)

            ws = websocket.WebSocketApp(
                server_url,
                on_open=lambda ws: print("Connected to server"),
                on_message=forward_to_ble,
                on_error=lambda ws, error: print(f"Error: {error}"),
                on_close=lambda ws, status_code, msg: print(f"Disconnected from server: {status_code} {msg}"),
            )
            ws.run_forever()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if ble_client.is_connected:
            await ble_client.disconnect()
            print("Disconnected from the device.")


async def main():
    ble_client = await find_ble_device()

    parser = argparse.ArgumentParser(description="WebSocket client")
    parser.add_argument("ip", nargs="?", default="localhost", help="Server IP address")
    parser.add_argument("-p", "--port", default="5000", help="Server port")
    args = parser.parse_args()

    ip = args.ip
    port = args.port
    server_url = f"ws://{ip}:{port}/drone"
    print(f"Connecting to {server_url}...")

    while True:
        await connect_and_reroute(ble_client, server_url)
        print("Disconnected. Attempting to reconnect...")
        await asyncio.sleep(5)  # Wait before trying to reconnect


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program terminated.")
