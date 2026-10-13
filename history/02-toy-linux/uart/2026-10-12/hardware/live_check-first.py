import re
from pathlib import Path
import time
import serial

output = Path(__file__).resolve().parent / 'live-console.log'
transcript = bytearray()
with serial.Serial('COM5', 1000000, timeout=.1, write_timeout=5,
                   rtscts=False, dsrdtr=False) as port:
    port.reset_input_buffer()
    port.write(b'echo HARDWARE_RC:$?;uname -a;grep MemTotal /proc/meminfo;echo FPGA_LIVE_DONE\n')
    port.flush()
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        transcript.extend(port.read(4096))
        if re.search(rb'(?:^|\n)FPGA_LIVE_DONE\r*\n', transcript):
            break
output.write_bytes(transcript)
print(transcript.decode(errors='replace'))
assert re.search(rb'(?:^|\n)HARDWARE_RC:0\r*\n', transcript)
assert b'Linux buckyball 6.6.0' in transcript
assert b'MemTotal:' in transcript
assert re.search(rb'(?:^|\n)FPGA_LIVE_DONE\r*\n', transcript)
print('PASS LIVE_LINUX_SHELL_AND_TEST_EXIT_STATUS')
