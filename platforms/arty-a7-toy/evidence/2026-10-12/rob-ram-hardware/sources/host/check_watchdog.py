"""在已启动的 Linux 控制台验证正常退出、非零退出、超时及 watcher 回收。"""

import argparse
import json
from pathlib import Path
import re
import time
import uuid

from check_linux_gemmini import bounded_command
from ftdi_transport import D2xxPort

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="COM5")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    out = args.output or ROOT / "build" / (
        "watchdog-" + time.strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:8]
    )
    out.mkdir(parents=True, exist_ok=False)
    cases = [("/bin/busybox true", 0), ("/bin/busybox false", 1),
             ("/bin/busybox sleep 5", 137)]
    result = {"result": "RUNNING", "cases": [], "flash_written": False}
    try:
        with D2xxPort(args.port, timeout_seconds=120) as port:
            with (out / "check.log").open("wb") as log:
                def run(command, marker):
                    port.write(command.encode())
                    buffer = bytearray()
                    deadline = time.monotonic() + 15
                    while time.monotonic() < deadline:
                        block = port.read(4096)
                        buffer.extend(block)
                        log.write(block)
                        log.flush()
                        match = re.search(rb"(?:^|\n)" + marker.encode()
                                          + rb":(\d+)\r*\n", buffer)
                        if match:
                            return int(match[1])
                    raise TimeoutError("Watchdog check response timeout")

                for index, (program, expected) in enumerate(cases):
                    marker = f"WATCH_SELF_{index}"
                    code = run(bounded_command(program, marker, seconds=1), marker)
                    if code != expected:
                        raise RuntimeError(f"{program}: exit {code}, expected {expected}")
                    marker = f"WATCH_REAP_{index}"
                    alive = run(f"kill -0 $w 2>/dev/null; "
                                f"printf '\\n{marker}:%s\\n' $?\n", marker)
                    if alive == 0:
                        raise RuntimeError("Watcher remains after explicit wait")
                    result["cases"].append({"program": program, "exit_code": code,
                                            "watcher_alive_rc": alive, "expected": True})
                    print(f"PASS watchdog case={index} exit={code} watcher_reaped=True")
        result["result"] = "PASS_WATCHDOG_SUCCESS_FAILURE_TIMEOUT_AND_REAP"
    except BaseException as error:
        result.update(result="FAIL", error=str(error))
        raise
    finally:
        (out / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("RESULT " + str(out / "RESULT.json"))


if __name__ == "__main__":
    main()
