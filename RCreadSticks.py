import ctypes
from dataclasses import dataclass
from typing import Dict, List, Optional

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
            "X": self._map_axis(self.dwXpos),
            "Y": self._map_axis(self.dwYpos),
            "Z": self._map_axis(self.dwZpos),
            "RX": self._map_axis(self.dwRpos),
            "RY": self._map_axis(self.dwUpos),
            "RZ": self._map_axis(self.dwVpos),
        }
        self.buttons = [self.dwButtons & 2 ** b != 0 for b in range(n_buttons)]

    def _map_axis(self, raw_value):
        # Assuming raw_value is from 0 to 65535 for most joysticks
        neutral_value = 32767  # Neutral position, the center value
        max_value = 65535  # Maximum possible joystick value (for 16-bit input)
        
        # Normalize to -127 to +127
        # We subtract neutral_value to center the axis at 0.
        normalized_value = ((raw_value - neutral_value) * 127) // (max_value // 2)
        
        # Clamp the value to the range -127 to +127
        mapped_value = max(min(normalized_value, 127), -127)
        
        # Treat values between -2 and +2 as 0
        if -2 <= mapped_value <= 2:
            mapped_value = 0
            
        return mapped_value


def get_joysticks() -> List[Joystick]:
    ret = []
    for i in range(_joyGetNumDevs()):
        caps_buf = _joyGetDevCaps(i)
        if caps_buf is not None:
            joy = Joystick(i)
            joy._load(caps_buf)
            ret.append(joy)
    return ret

if __name__ == '__main__':
    import sys
    import time

    joysticks = get_joysticks()
    if len(joysticks) == 0:
        print("No joysticks")
        sys.exit(1)
    joystick = joysticks[0]
    print(f"Joystick connected: ID {joystick.id}, Name {joystick.szPname}")

    while True:
        values = joystick.get()
        if values:
            # Read the left stick (X, Y) and right stick (Z, RZ)
            x_axis_value = values.axes["X"]
            y_axis_value = values.axes["Y"]
            z_axis_value = values.axes["Z"]
            rz_axis_value = values.axes["RZ"]

            # Print the values for debugging
            print(f"Joystick values - X: {x_axis_value}, Y: {y_axis_value}, Z: {z_axis_value}, RZ: {rz_axis_value}")

        time.sleep(0.1)
