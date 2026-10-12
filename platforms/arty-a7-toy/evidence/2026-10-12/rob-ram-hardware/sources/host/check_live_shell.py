"""回归后检查 Linux 控制台、空闲内存和已回收的 watchdog。"""
import argparse
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'host'))
from ftdi_transport import D2xxPort


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default='COM5')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False, parents=True)
    commands = [
        b'kill -0 "$w" 2>/dev/null; printf "\\nWATCHDOG_ALIVE_RC:%s\\n" "$?"\n',
        b'while read a b c; do case "$a" in MemTotal:|MemAvailable:) printf "%s %s %s\\n" "$a" "$b" "$c";; esac; done < /proc/meminfo; printf "LIVE_MEM_DONE\\n"\n',
    ]
    result = {'flash_written': False, 'configuration_changed': False}
    with D2xxPort(args.port, timeout_seconds=120) as port:
        with (args.output / 'post-console.log').open('wb') as log:
            for index, command in enumerate(commands):
                port.write(command)
                buffer = bytearray()
                deadline = time.monotonic() + 30
                pattern = (rb'(?:^|\n)WATCHDOG_ALIVE_RC:(\d+)\r*\n' if index == 0
                           else rb'(?:^|\n)LIVE_MEM_DONE\r*\n')
                while time.monotonic() < deadline:
                    data = port.read(4096)
                    buffer.extend(data)
                    log.write(data)
                    log.flush()
                    match = re.search(pattern, buffer)
                    if match:
                        break
                else:
                    raise TimeoutError('Post-test live console timeout')
                print(buffer.decode(errors='replace'))
                if index == 0:
                    result['watchdog_alive_rc'] = int(match[1])
                    if int(match[1]) == 0:
                        raise ValueError('Last watchdog still running')
                else:
                    for name in ['MemTotal', 'MemAvailable']:
                        match = re.search(name.encode() + rb':\s+(\d+) kB\r*\n', buffer)
                        if not match:
                            raise ValueError('Missing live memory field')
                        result[name + '_kib'] = int(match[1])
            result['uart_latency_restored_ms'] = port.original_latency.value
    result['result'] = 'PASS_POST_TEST_LIVE_SHELL'
    (args.output / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
