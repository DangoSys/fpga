import json
from pathlib import Path
import re
import sys
import time

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "host"))
from ftdi_transport import D2xxPort

out = root / "build/hardware-gemmini-20261012-4de39d38"
commands = [
    b"kill -0 \"$w\" 2>/dev/null; printf '\\nWATCHDOG_ALIVE_RC:%s\\n' \"$?\"\n",
    b"while read a b c; do case \"$a\" in MemTotal:|MemAvailable:) printf '%s %s %s\\n' \"$a\" \"$b\" \"$c\";; esac; done < /proc/meminfo; printf 'LIVE_MEM_DONE\\n'\n",
]
result = {"flash_written": False, "configuration_changed": False}
with D2xxPort("COM5", timeout_seconds=120) as port:
    with (out / "post-console.log").open("wb") as log:
        for index, command in enumerate(commands):
            port.write(command)
            buffer = bytearray()
            deadline = time.monotonic() + 30
            pattern = rb"(?:^|\n)WATCHDOG_ALIVE_RC:(\d+)\r*\n" if index == 0 else rb"(?:^|\n)LIVE_MEM_DONE\r*\n"
            while time.monotonic() < deadline:
                data = port.read(4096)
                buffer.extend(data)
                log.write(data)
                match = re.search(pattern, buffer)
                if match:
                    break
            else:
                raise TimeoutError("Post-test live console timeout")
            print(buffer.decode(errors="replace"))
            if index == 0:
                result["watchdog_alive_rc"] = int(match[1])
                if int(match[1]) == 0:
                    raise ValueError("Last watchdog still running")
            else:
                for name in ["MemTotal", "MemAvailable"]:
                    match = re.search(name.encode() + rb":\s+(\d+) kB\r*\n", buffer)
                    if not match:
                        raise ValueError("Missing live memory field")
                    result[name + "_kib"] = int(match[1])
result["result"] = "PASS_POST_TEST_LIVE_SHELL"
result["uart_latency_restored_ms"] = 16
(out / "POST_RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
