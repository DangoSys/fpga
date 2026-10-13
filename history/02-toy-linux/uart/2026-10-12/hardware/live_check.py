import re
from pathlib import Path
import time
import serial

output = Path(__file__).resolve().parent / 'live-console.log'
transcript = bytearray()
with serial.Serial('COM5', 1000000, timeout=.1, write_timeout=5,
                   rtscts=False, dsrdtr=False) as port:
    port.reset_input_buffer()
    port.write(b'read version </proc/version;echo KERNEL:$version;read memory </proc/meminfo;echo MEMORY:$memory;echo FPGA_LIVE_DONE\n')
    port.flush()
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        transcript.extend(port.read(4096))
        if re.search(rb'(?:^|\n)FPGA_LIVE_DONE\r*\n', transcript):
            break
output.write_bytes(transcript)
print(transcript.decode(errors='replace'))
first_check = output.with_name('live-console-first.log').read_bytes()
assert re.search(rb'(?:^|\n)HARDWARE_RC:0\r*\n', first_check)
assert b'KERNEL:Linux version 6.6.0' in transcript
assert b'MemTotal:' in transcript
assert re.search(rb'(?:^|\n)FPGA_LIVE_DONE\r*\n', transcript)
print('PASS LIVE_LINUX_SHELL_AND_TEST_EXIT_STATUS')
