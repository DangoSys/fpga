from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
out = root / 'build/rob-hardware-session-20261012'
out.mkdir(exist_ok=False)
bit = root / 'build/toy-a7-rob-ram-20261012-2ebcbc31/board/toy_a7.bit'
payload = root / 'build/linux-gemmini-20261012-e8e89f4c/fw_payload.bin'
build = root / 'build/linux-gemmini-20261012-e8e89f4c/LINUX_GEMMINI_BUILD.json'
expected = 'dec8dcaea14b56db49ef8166d1605034695658f55f02dce73d4455fbc078ee5c'
assert hashlib.sha256(bit.read_bytes()).hexdigest() == expected
start = datetime.now(timezone(timedelta(hours=8)))
command = [sys.executable, '-u', str(root/'host/check_linux_gemmini.py'),
           '--payload', str(payload), '--build-result', str(build), '--bitstream', str(bit),
           '--expected-bit-sha256', expected,
           '--vivado', 'D:/Xilinx/2025.1/Vivado/bin/vivado.bat', '--port', 'COM5']
record = {'started_at':start.isoformat(), 'deadline':(start+timedelta(seconds=3600)).isoformat(),
          'timeout_seconds':3600, 'command':command, 'flash_written':False,
          'script_sha256':hashlib.sha256((root/'host/check_linux_gemmini.py').read_bytes()).hexdigest(),
          'uart_serial':'210319BCC5FCB'}
(out/'SESSION.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
try:
    result = subprocess.run(command,cwd=root,timeout=3600,check=True)
    record['exit_code']=result.returncode
finally:
    record['finished_at']=datetime.now(timezone(timedelta(hours=8))).isoformat()
    (out/'SESSION.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
