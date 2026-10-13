"""Windows UART B 的 D2XX 运输适配；关闭时恢复原延迟，不访问 JTAG A。"""

import ctypes as c
import time


class D2xxPort:
    def __init__(self, port, baudrate=1000000, timeout_seconds=3600):
        import serial.tools.list_ports

        matches = [item for item in serial.tools.list_ports.comports() if item.device == port]
        if len(matches) != 1:
            raise RuntimeError("Expected exactly one selected UART port")
        device = matches[0]
        if (device.vid, device.pid) != (0x0403, 0x6010) or not device.serial_number.endswith("B"):
            raise RuntimeError("Expected FT2232 UART B; do not use JTAG A")
        self.api = c.WinDLL("C:/Windows/System32/ftd2xx.dll")
        signatures = {
            "FT_OpenEx": [c.c_void_p, c.c_uint32, c.POINTER(c.c_void_p)],
            "FT_Close": [c.c_void_p],
            "FT_GetLatencyTimer": [c.c_void_p, c.POINTER(c.c_ubyte)],
            "FT_SetLatencyTimer": [c.c_void_p, c.c_ubyte],
            "FT_SetBaudRate": [c.c_void_p, c.c_uint32],
            "FT_SetDataCharacteristics": [c.c_void_p, c.c_ubyte, c.c_ubyte, c.c_ubyte],
            "FT_SetFlowControl": [c.c_void_p, c.c_ushort, c.c_ubyte, c.c_ubyte],
            "FT_SetTimeouts": [c.c_void_p, c.c_uint32, c.c_uint32],
            "FT_Purge": [c.c_void_p, c.c_uint32],
            "FT_Read": [c.c_void_p, c.c_void_p, c.c_uint32, c.POINTER(c.c_uint32)],
            "FT_Write": [c.c_void_p, c.c_void_p, c.c_uint32, c.POINTER(c.c_uint32)],
            "FT_GetQueueStatus": [c.c_void_p, c.POINTER(c.c_uint32)],
        }
        for name, signature in signatures.items():
            method = getattr(self.api, name)
            method.argtypes = signature
            method.restype = c.c_uint32
        self.handle = c.c_void_p()
        self.original_latency = c.c_ubyte()
        self.closed = True
        self.deadline = time.monotonic() + timeout_seconds
        self.call("FT_OpenEx", c.cast(c.c_char_p(device.serial_number.encode()), c.c_void_p),
                  1, c.byref(self.handle))
        self.closed = False
        self.latency_known = False
        try:
            self.call("FT_GetLatencyTimer", self.handle, c.byref(self.original_latency))
            self.latency_known = True
            self.call("FT_SetLatencyTimer", self.handle, 2)
            self.call("FT_SetBaudRate", self.handle, baudrate)
            self.call("FT_SetDataCharacteristics", self.handle, 8, 0, 0)
            self.call("FT_SetFlowControl", self.handle, 0, 0, 0)
            self.call("FT_SetTimeouts", self.handle, 100, 5000)
            self.call("FT_Purge", self.handle, 3)
        except BaseException:
            self.close()
            raise
        print(f"D2XX UART B {port}: latency {self.original_latency.value}->2 ms", flush=True)

    def call(self, name, *args):
        status = getattr(self.api, name)(*args)
        if status:
            raise OSError(f"{name}: FT_STATUS {status}")

    def check_deadline(self):
        if time.monotonic() > self.deadline:
            raise TimeoutError("One-hour hardware-session timeout")

    def read(self, count):
        self.check_deadline()
        if not count:
            return b""
        available = c.c_uint32()
        self.call("FT_GetQueueStatus", self.handle, c.byref(available))
        size = min(count, available.value) if available.value else 1
        buffer = c.create_string_buffer(size)
        received = c.c_uint32()
        self.call("FT_Read", self.handle, buffer, size, c.byref(received))
        return buffer.raw[:received.value]

    def write(self, data):
        self.check_deadline()
        buffer = c.create_string_buffer(data)
        written = c.c_uint32()
        self.call("FT_Write", self.handle, buffer, len(data), c.byref(written))
        if written.value != len(data):
            raise TimeoutError("D2XX short write")
        return written.value

    def flush(self):
        pass  # FT_Write completes its synchronous USB transfer before returning.

    def close(self):
        if not self.closed:
            try:
                if self.latency_known:
                    self.call("FT_SetLatencyTimer", self.handle, self.original_latency.value)
            finally:
                self.call("FT_Close", self.handle)
                self.closed = True
                print(f"D2XX closed; latency restored to {self.original_latency.value} ms", flush=True)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
