import argparse
import asyncio
import threading

from bleak import BleakScanner, BleakClient
import struct
import websocket

# Bluetooth-related constants
DEVICE_NAME = "DJI_REMOTE_TRPY"  # The advertised BLE name
SERVICE_UUID = "1fbcdfb1-8e73-4296-9057-a6ee3133902a"
CHAR_UUID = "d97e4ec1-d3c4-4952-a421-884719fe35f7"

# Define the format of the struct: 6 int16_t values
STRUCT_FORMAT = "<4h"  # Little-endian (<), 6 short integers (h)


def parse_message(message):
    """ Returns roll, pitch, yaw, throttle, camera, command from the message """
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
            print(f'Received: {roll=}, {pitch=}, {yaw=}, {throttle=}, {camera=}, {command=}')
            return int(roll), int(pitch), int(yaw), int(throttle)
    except ValueError:
        raise ValueError("Invalid message format")


async def run(server_url):
    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover(timeout=5.0)
    target_device = None

    for d in devices:
        if d.name == DEVICE_NAME:
            target_device = d
            break

    if not target_device:
        print(f"Device '{DEVICE_NAME}' not found. Check your device is advertising.")
        return
    else:
        print(f"Found {DEVICE_NAME} at address {target_device.address}. Connecting...")

    async with BleakClient(target_device.address) as client:
        if client.is_connected:
            print(f"Connected to {DEVICE_NAME}!")
        else:
            print(f"Failed to connect to {DEVICE_NAME}.")
            return

        last_msg = ""

        def set_last_msg(ws, msg):
            nonlocal last_msg
            last_msg = msg

        ws = websocket.WebSocketApp(
            server_url,
            on_open=lambda ws: print("Connected to server"),
            on_message=set_last_msg,
            on_error=lambda ws, error: print(f"Error: {error}"),
            on_close=lambda ws, status_code, msg: print(f"Disconnected from server: {status_code} {msg}"),
        )

        def run_ws_forever(ws):
            ws.run_forever()
        ws_thread = threading.Thread(target=run_ws_forever, args=(ws,))
        ws_thread.start()

        try:
            while True:
                if last_msg != "":
                    roll, pitch, yaw, throttle = parse_message(last_msg)
                    throttle = int(throttle) #2090
                    roll = int(roll) #90
                    pitch = int(pitch) #1065
                    yaw = int(yaw)

                    # Pack the data into a binary format using the struct module
                    data = struct.pack(STRUCT_FORMAT, throttle, yaw, pitch, roll)#, extra1, extra2)

                    print("Sending data:", [throttle, yaw, pitch, roll])#, extra1, extra2])

                    # Write the 12-byte array to the specified characteristic
                    await client.write_gatt_char(CHAR_UUID, data)
                    last_msg = ""

                await asyncio.sleep(0.05)

        except KeyboardInterrupt:
            print("Stopping server...")
            ws.close()
            ws_thread.join()
            print("Disconnected from server")



def main():
    parser = argparse.ArgumentParser(description="WebSocket client")
    parser.add_argument("ip", nargs="?", default="82.81.197.132", help="Server IP address")
    parser.add_argument("-p", "--port", default="5000", help="Server port")
    args = parser.parse_args()

    ip = args.ip
    port = args.port
    server_url = f"ws://{ip}:{port}/drone"

    asyncio.run(run(server_url))


if __name__ == "__main__":
    main()
