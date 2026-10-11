"""Local bring-up transport: reuse the unmodified loader with FTDI D2XX.

Only the enumerated UART B interface is opened. Restore its original latency
when closing; no registry, EEPROM, JTAG channel, RTL or loader protocol changes.
"""
import ctypes as c
import hashlib
import json
from pathlib import Path
import runpy
import struct
import sys
import time

ROOT = Path('D:/Verilog_Dev/fpga-arty-a7-pr/platforms/arty-a7-toy')
OUT = Path(__file__).resolve().parent
PAYLOAD = Path('D:/Verilog_Dev/toy-a7-gemmini-correct-20261010/build/board-software/fw_payload.bin')
SERIAL = b'210319BCC5FCB'
EXPECTED = 'eb2ee34cc1a744498ac63b4e3fae425d4bb06be422ae6d41bd1ead696201134f'
sys.path.insert(0, str(ROOT / 'host'))
from load import Loader


class D2xxPort:
    def __init__(self, port, baudrate, **kwargs):
        import serial.tools.list_ports
        ports = [p for p in serial.tools.list_ports.comports() if p.device == port]
        assert len(ports) == 1 and ports[0].serial_number == SERIAL.decode()
        assert (ports[0].vid, ports[0].pid) == (0x0403, 0x6010)
        self.api = c.WinDLL('C:/Windows/System32/ftd2xx.dll')
        types = {
            'FT_OpenEx': [c.c_void_p, c.c_uint32, c.POINTER(c.c_void_p)],
            'FT_Close': [c.c_void_p],
            'FT_GetLatencyTimer': [c.c_void_p, c.POINTER(c.c_ubyte)],
            'FT_SetLatencyTimer': [c.c_void_p, c.c_ubyte],
            'FT_SetBaudRate': [c.c_void_p, c.c_uint32],
            'FT_SetDataCharacteristics': [c.c_void_p, c.c_ubyte, c.c_ubyte, c.c_ubyte],
            'FT_SetFlowControl': [c.c_void_p, c.c_ushort, c.c_ubyte, c.c_ubyte],
            'FT_SetTimeouts': [c.c_void_p, c.c_uint32, c.c_uint32],
            'FT_Purge': [c.c_void_p, c.c_uint32],
            'FT_Read': [c.c_void_p, c.c_void_p, c.c_uint32, c.POINTER(c.c_uint32)],
            'FT_Write': [c.c_void_p, c.c_void_p, c.c_uint32, c.POINTER(c.c_uint32)],
            'FT_GetQueueStatus': [c.c_void_p, c.POINTER(c.c_uint32)],
        }
        for name, args in types.items():
            method = getattr(self.api, name)
            method.argtypes = args
            method.restype = c.c_uint32
        self.handle = c.c_void_p()
        self.latency = c.c_ubyte()
        self.deadline = time.monotonic() + 3600
        self.closed = True
        self.call('FT_OpenEx', c.cast(c.c_char_p(SERIAL), c.c_void_p), 1, c.byref(self.handle))
        self.closed = False
        try:
            self.call('FT_GetLatencyTimer', self.handle, c.byref(self.latency))
            self.call('FT_SetLatencyTimer', self.handle, 2)
            self.call('FT_SetBaudRate', self.handle, baudrate)
            self.call('FT_SetDataCharacteristics', self.handle, 8, 0, 0)
            self.call('FT_SetFlowControl', self.handle, 0, 0, 0)
            self.call('FT_SetTimeouts', self.handle, 100, 5000)
            self.call('FT_Purge', self.handle, 3)
        except BaseException:
            self.close()
            raise
        print(f'D2XX UART B {port}: {baudrate} baud, latency {self.latency.value}->2 ms', flush=True)

    def call(self, name, *args):
        status = getattr(self.api, name)(*args)
        if status != 0:
            raise OSError(f'{name}: FT_STATUS {status}')

    def reset_input_buffer(self):
        self.call('FT_Purge', self.handle, 1)

    def read(self, count):
        if time.monotonic() > self.deadline:
            raise TimeoutError('One-hour hardware load timeout')
        if count == 0:
            return b''
        available = c.c_uint32()
        self.call('FT_GetQueueStatus', self.handle, c.byref(available))
        size = min(count, available.value) if available.value else min(count, 1)
        buffer = c.create_string_buffer(size)
        received = c.c_uint32()
        self.call('FT_Read', self.handle, buffer, size, c.byref(received))
        return buffer.raw[:received.value]

    def write(self, data):
        if time.monotonic() > self.deadline:
            raise TimeoutError('One-hour hardware load timeout')
        buffer = c.create_string_buffer(data)
        written = c.c_uint32()
        self.call('FT_Write', self.handle, buffer, len(data), c.byref(written))
        if written.value != len(data):
            raise TimeoutError('D2XX short write')
        return written.value

    def flush(self):
        # FT_Write has completed its synchronous USB write before returning.
        pass

    def close(self):
        if not self.closed:
            try:
                self.call('FT_SetLatencyTimer', self.handle, self.latency.value)
            finally:
                self.call('FT_Close', self.handle)
                self.closed = True
                print(f'D2XX closed; restored UART latency {self.latency.value} ms', flush=True)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def main():
    assert hashlib.sha256(PAYLOAD.read_bytes()).hexdigest() == EXPECTED
    started = time.monotonic()
    if '--probe' in sys.argv:
        with D2xxPort('COM5', 1000000) as port:
            loader = Loader(port)
            info = loader.request(4)
            assert info == b'TA7\x02' + struct.pack('<II', 268435456, 25000000)
            payload = PAYLOAD.read_bytes()
            for offset in range(0, 4096, 256):
                chunk = payload[offset:offset+256]
                loader.request(1, 0x80000000+offset, len(chunk), chunk)
                assert loader.request(2, 0x80000000+offset, len(chunk)) == chunk
            print(f'PASS D2XX 4096-byte write/readback elapsed={time.monotonic()-started:.3f}s', flush=True)
        return
    import serial
    original = serial.Serial
    serial.Serial = D2xxPort
    sys.argv = [str(ROOT / 'host/load.py'), '--port', 'COM5', '--check-linux',
                '--console-seconds', '300', '--transcript', str(OUT / 'linux-console.log'), str(PAYLOAD)]
    result = {'bitstream_sha256': 'ccc33c511e613561fb9dd1e9c847bd3b84037da1d078c44cd3de197d55dffde1',
              'payload_sha256': EXPECTED, 'payload_bytes': PAYLOAD.stat().st_size,
              'port': 'COM5', 'uart_serial': SERIAL.decode(), 'physical_board_revision': 'unknown',
              'transport': 'installed FTDI D2XX, temporary 2ms latency; original host loader',
              'result': 'RUNNING'}
    (OUT / 'HARDWARE_RESULT.json').write_text(json.dumps(result, indent=2)+'\n')
    try:
        runpy.run_path(str(ROOT / 'host/load.py'), run_name='__main__')
        result.update(result='PASS_HARDWARE_LOAD_AND_LINUX_CHECK', physical_linux_boot_tested=True)
    except BaseException as error:
        result.update(result='FAILED', error=repr(error))
        raise
    finally:
        serial.Serial = original
        result['elapsed_seconds'] = time.monotonic()-started
        (OUT / 'HARDWARE_RESULT.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
