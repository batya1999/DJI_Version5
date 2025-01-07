import asyncio
import websockets
import ctypes
from dataclasses import dataclass
from typing import Dict, List, Optional
import time

try:
    winmmdll = ctypes.WinDLL('winmm.dll')

    _joyGetNumDevs_proto = ctypes.WINFUNCTYPE(ctypes.c_uint)
    _joyGetNumDevs_func = _joyGetNumDevs_proto(("joyGetNumDevs", winmmdll))

    _joyGetDevCaps_proto = ctypes.WINFUNCTYPE(ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint)
    _joyGetDevCaps_param = (1, "uJoyID", 0), (1, "pjc", None), (1, "cbjc", 0)
    _joyGetDevCaps_func = _joyGetDevCaps_proto(("joyGetDevCapsW", winmmdll), _joyGetDevCaps_param)

    _joyGetPosEx_proto = ctypes.WINFUNCTYPE(ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p)
    _joyGetPosEx_param = (1, "uJoyID", 0), (1, "pji", None)
    _joyGetPosEx_func = _joyGetPosEx_proto(("joyGetPosEx", winmmdll), _joyGetPosEx_param)
except:
    winmmdll = None

JOYERR_NOERROR = 0
JOY_RETURNY = 0x00000002
_CAPS_SIZE_W = 728
_CAPS_OFFSET_V = 4 + 32 * 2

def _joyGetNumDevs():
    try:
        num = _joyGetNumDevs_func()
    except:
        num = 0
    return num

def _joyGetDevCaps(uJoyID):
    try:
        buffer = (ctypes.c_ubyte * _CAPS_SIZE_W)()
        p1 = ctypes.c_uint(uJoyID)
        p2 = ctypes.cast(buffer, ctypes.c_void_p)
        p3 = ctypes.c_uint(_CAPS_SIZE_W)
        ret_val = _joyGetDevCaps_func(p1, p2, p3)
        ret = None if ret_val != JOYERR_NOERROR else buffer
    except:
        ret = None
    return ret

def _joyGetPosEx(uJoyID):
    try:
        buffer = (ctypes.c_uint32 * (_JOYINFO_SIZE // 4))()
        buffer[0] = _JOYINFO_SIZE
        buffer[1] = JOY_RETURNY
        p1 = ctypes.c_uint(uJoyID)
        p2 = ctypes.cast(buffer, ctypes.c_void_p)
        ret_val = _joyGetPosEx_func(p1, p2)
        ret = None if ret_val != JOYERR_NOERROR else buffer
    except:
        ret = None
    return ret

@dataclass
class ChannelCaps:
    min: int
    max: int

@dataclass
class Joystick:
    id: int
    axes: Dict[str, ChannelCaps]
    buttons: int

    def __init__(self, uJoyID):
        self.id = uJoyID
        self.loaded = False

    def _load(self, buffer):
        ushort_array = (ctypes.c_uint16 * 2).from_buffer(buffer)
        self.wMid, self.wPid = ushort_array

        wchar_array = (ctypes.c_wchar * 32).from_buffer(buffer, 4)
        self.szPname = ctypes.cast(wchar_array, ctypes.c_wchar_p).value

        uint_array = (ctypes.c_uint32 * 19).from_buffer(buffer, _CAPS_OFFSET_V)
        self.wXmin, self.wXmax, self.wYmin, self.wYmax, self.wZmin, self.wZmax, \
            self.wNumButtons, self.wPeriodMin, self.wPeriodMax, \
            self.wRmin, self.wRmax, self.wUmin, self.wUmax, self.wVmin, self.wVmax, \
            self.wCaps, self.wMaxAxes, self.wNumAxes, self.wMaxButtons = uint_array

        self.axes = {
            "X": ChannelCaps(self.wXmin, self.wXmax),
            "Y": ChannelCaps(self.wYmin, self.wYmax),
            "Z": ChannelCaps(self.wZmin, self.wZmax),
            "RX": ChannelCaps(self.wRmin, self.wRmax),
            "RY": ChannelCaps(self.wUmin, self.wUmax),
            "RZ": ChannelCaps(self.wVmin, self.wVmax),
        }
        self.buttons = self.wNumButtons

    def get(self) -> Optional["JoyValues"]:
        if not self.loaded:
            self._load(_joyGetDevCaps(self.id))
        buf = _joyGetPosEx(self.id)
        if buf is None:
            return None
        return JoyValues(buf, self.buttons)

_JOYINFO_SIZE = 52

@dataclass
class JoyValues:
    axes: Dict[str, int]
    buttons: List[int]

    def __init__(self, buffer, n_buttons):
        uint_array = (ctypes.c_uint32 * (_JOYINFO_SIZE // 4)).from_buffer(buffer)
        self.dwSize, self.dwFlags, \
            self.dwXpos, self.dwYpos, self.dwZpos, self.dwRpos, self.dwUpos, self.dwVpos, \
            self.dwButtons, self.dwButtonNumber, self.dwPOV, self.dwReserved1, self.dwReserved2 = uint_array

        self.axes = {
            "X": self.dwXpos,
            "Y": self.dwYpos,
            "Z": self.dwZpos,
            "RX": self.dwRpos,
            "RY": self.dwUpos,
            "RZ": self.dwVpos,
        }
        self.buttons = [self.dwButtons & 2 ** b != 0 for b in range(n_buttons)]

def get_joysticks() -> List[Joystick]:
    ret = []
    for i in range(_joyGetNumDevs()):
        caps_buf = _joyGetDevCaps(i)
        if caps_buf is not None:
            joy = Joystick(i)
            joy._load(caps_buf)
            ret.append(joy)
    return ret

# WebSocket server code
async def echo(websocket, path):
    print("Client connected")
    
    # Queue for messages to send to the client
    message_queue = asyncio.Queue()

    # Background task to handle sending messages to the client
    async def send_messages():
        while True:
            server_message = await message_queue.get()
            if server_message is None:  # Exit signal
                print("Closing connection...")
                await websocket.close()
                break
            await websocket.send(server_message)

    # Task to get user input asynchronously
    async def get_user_input():
        while True:
            user_input = await asyncio.to_thread(input, "Enter a message to send to the client (or 'exit' to quit): ")
            if user_input.lower() == "exit":
                await message_queue.put(None)  # Signal to stop
                break
            if user_input.lower() == "takeoff":
                # Send takeoff command to the client
                command_message = "takeoff"
                await message_queue.put(command_message)
            else:
                await message_queue.put(user_input)

    # Task to handle receiving messages from the client
    async def receive_messages():
        async for message in websocket:
            print(f"Received from client: {message}")

    # Task to handle joystick inputs and send them to the WebSocket client
    async def joystick_input():
        joysticks = get_joysticks()
        if len(joysticks) == 0:
            print("No joysticks detected!")
            return

        joystick = joysticks[0]
        print(f"Joystick connected: ID {joystick.id}, Name {joystick.szPname}")

        neutral_range = (32000, 33500)  # Neutral range for X and Y axes
        tolerance = 0  # Allow a small tolerance for minor movements

        while True:
            values = joystick.get()
            if values:
                # Read the left stick (X and Y axis)
                x_axis_value = values.axes["X"]
                y_axis_value = values.axes["Y"]

                # print(f"Joystick values - X: {x_axis_value}, Y: {y_axis_value}")  # Log values

                # Check if the joystick is in the neutral zone
                if neutral_range[0] - tolerance <= x_axis_value <= neutral_range[1] + tolerance and \
                neutral_range[0] - tolerance <= y_axis_value <= neutral_range[1] + tolerance:
                    # await message_queue.put("s")
                    pass
                else:
                    # Left stick movement logic
                    if x_axis_value < neutral_range[0] - tolerance:  # Threshold for left movement
                        await message_queue.put("left")  # Send Left
                    elif x_axis_value > neutral_range[1] + tolerance:  # Threshold for right movement
                        await message_queue.put("right")  # Send Right

                    if y_axis_value < neutral_range[0] - tolerance:  # Threshold for down movement
                        await message_queue.put("backward")  # Send Down
                    elif y_axis_value > neutral_range[1] + tolerance:  # Threshold for up movement
                        await message_queue.put("forward")  # Send Up

            await asyncio.sleep(0.1)



    # Run all tasks concurrently
    await asyncio.gather(send_messages(), get_user_input(), receive_messages(), joystick_input())

# Start the server
async def main():
    async with websockets.serve(echo, "192.168.8.122", 5000):
        print("WebSocket server listening on ws://192.168.8.122:5000")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
