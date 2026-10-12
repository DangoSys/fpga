import json
from pathlib import Path
import re
import sys
import time

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "host"))
from check_linux_gemmini import bounded_command
from ftdi_transport import D2xxPort

out = root / "build/hardware-gemmini-20261012-88d47bdc"
build = json.loads((root / "build/linux-gemmini-20261012-e8e89f4c/LINUX_GEMMINI_BUILD.json").read_text())
maximum = max(len(bounded_command("/root/" + name, "WB_TEST_RC_14").encode())
              for name in build["workloads"])
print("MAX_CONSOLE_COMMAND_BYTES", maximum)
cases = [("/bin/busybox true", 0), ("/bin/busybox false", 1), ("/bin/busybox sleep 5", 137)]
result = {"cases": [], "max_console_command_bytes": maximum, "flash_written": False}
with D2xxPort("COM5", timeout_seconds=120) as port:
    with (out / "watchdog-check.log").open("wb") as log:
        def run(command, marker):
            port.write(command.encode())
            buffer = bytearray()
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                data = port.read(4096)
                buffer.extend(data)
                log.write(data)
                log.flush()
                match = re.search(rb"(?:^|\n)" + marker.encode() + rb":(\d+)\r*\n", buffer)
                if match:
                    print(buffer.decode(errors="replace"))
                    return int(match[1])
            raise TimeoutError("Watchdog self-check response timeout")

        for index, (program, expected) in enumerate(cases):
            marker = f"WATCH_SELF_{index}"
            code = run(bounded_command(program, marker, seconds=1), marker)
            if code != expected:
                raise ValueError(f"Wrong watchdog result: {program} {code} != {expected}")
            marker = f"WATCH_REAP_{index}"
            alive = run(f"kill -0 $w 2>/dev/null; printf '\\n{marker}:%s\\n' $?\n", marker)
            if alive == 0:
                raise ValueError("Watcher remains after explicit wait")
            result["cases"].append({"program": program, "exit_code": code,
                                    "watcher_alive_rc": alive, "expected": True})
result["result"] = "PASS_WATCHDOG_SUCCESS_FAILURE_TIMEOUT_AND_REAP"
result["uart_latency_restored_ms"] = 16
(out / "WATCHDOG_RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
