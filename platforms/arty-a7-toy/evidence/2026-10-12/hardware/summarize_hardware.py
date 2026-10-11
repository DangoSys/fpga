import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

record = json.loads((ROOT / 'HARDWARE_RESULT.json').read_text())
assert record['result'] == 'PASS_HARDWARE_LOAD_AND_LINUX_CHECK'
program = (ROOT / 'program.log').read_text(errors='replace')
assert 'End of startup status: HIGH' in program
assert 'ARTY_JTAG_PROGRAMMED:' in program
load = (ROOT / 'load-and-linux.log').read_text(errors='replace')
assert 'Full readback passed; CPU started after 544.1s.' in load
console = (ROOT / 'linux-console.log').read_bytes()
checks = ['VM_COPY_ON_WRITE', 'VM_PAGE_PROTECTION', 'FP64_PROCESS_CONTEXT',
          'LINUX_TIMER', 'LINUX_SYSTEM_CHECK']
assert all(('PASS ' + check).encode() in console for check in checks)
assert b'Linux version 6.6.0' in console
assert b'~ # ' in console
first = (ROOT / 'live-console-first.log').read_bytes()
assert re.search(rb'(?:^|\n)HARDWARE_RC:0\r*\n', first)
live = (ROOT / 'live-console.log').read_bytes()
assert b'KERNEL:Linux version 6.6.0' in live
assert b'MEMORY:MemTotal: 245784 kB' in live
assert re.search(rb'(?:^|\n)FPGA_LIVE_DONE\r*\n', live)
record.update(jtag_programming='PASS', startup_status='HIGH',
              configuration='volatile FPGA SRAM',
              complete_payload_ddr_readback='PASS',
              verified_ddr_bytes=17409032, load_readback_seconds=544.1,
              linux_checks={name: 'PASS' for name in checks},
              system_check_process_exit_status=0, live_shell='PASS',
              linux_memtotal_kib=245784, uart_latency_restored_ms=16,
              hardware_gemmini_operator_tests_run=False,
              hardware_fp16_fp32_exhaustive_tests_run=False,
              coverage_notes=[
                  'Physical PCB revision remains unknown; this exact Rev E engineering image boots on the connected board.',
                  'SIGSEGV is intentional in the page-protection test; parent oracle passed.',
                  'First live probe used absent uname/grep symlinks; preserved. Shell builtins then read /proc successfully.',
                  'No flash programming, power measurements, long-duration stability or full 256MiB DDR sweep.',
              ])
record['evidence_sha256'] = {
    str(path.relative_to(ROOT)): sha(path)
    for path in sorted(ROOT.iterdir())
    if path.is_file() and path.name != 'HARDWARE_RESULT.json'
}
(ROOT / 'HARDWARE_RESULT.json').write_text(json.dumps(record, indent=2)+'\n')
print('PASS: JTAG, complete DDR image readback, physical Linux boot, five Linux checks and live shell')
