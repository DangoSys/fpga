"""用原生 Linux 进程验证协作锁及统一入口；不会执行 Gemmini 指令。"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--output", type=Path, default=ROOT / "build/gemmini-ownership-host")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    sources = [ROOT / "software/runtime" / name for name in
               ("gemmini_lease.c", "gemmini_lease.h", "gemmini_linux_entry.c")]
    sources += [ROOT / "tests/gemmini_lease_test.c", ROOT / "tests/gemmini_entry_mock.c"]
    sources.append(ROOT / "software/runtime/gemmini_concurrency.sh")
    commands = []
    transcript = []

    def run(command, expected=0, env=None, timeout=30):
        commands.append(list(map(str, command)))
        result = subprocess.run(command, text=True, capture_output=True,
                                timeout=timeout, env=env)
        transcript.append(result.stdout + result.stderr)
        if result.returncode != expected:
            raise RuntimeError(f"Exit {result.returncode}, expected {expected}: "
                               f"{command}\n{transcript[-1]}")
        return result

    flags = [args.cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
             "-I", str(ROOT / "software/runtime")]
    with tempfile.TemporaryDirectory(prefix="bb-gemmini-host-", dir=out) as folder:
        temporary = Path(folder)
        native = temporary / "lease-test"
        run(flags + [str(sources[0]), str(ROOT / "tests/gemmini_lease_test.c"),
                     "-o", str(native)])
        result = run([str(native), str(temporary)])
        assert "PASS GEMMINI_LEASE_HOST_TESTS cases=7 hardware_tested=0" in result.stdout
        wrapper = temporary / "entry-test"
        lock = temporary / "wrapper.lock"
        run(flags + [f'-DBB_GEMMINI_LOCK_PATH="{lock.as_posix()}"',
                     str(sources[0]), str(sources[2]),
                     str(ROOT / "tests/gemmini_entry_mock.c"), "-o", str(wrapper)])
        for _ in range(2):
            result = run([str(wrapper)])
            assert result.stdout.splitlines() == ["MOCK_DRAIN", "MOCK_WORKLOAD", "MOCK_DRAIN"]
            assert "GEMMINI_LEASE complete" in result.stderr
        environment = os.environ.copy()
        environment["BB_TEST_FAIL"] = "1"
        result = run([str(wrapper)], expected=1, env=environment)
        assert result.stdout.splitlines() == ["MOCK_DRAIN", "MOCK_WORKLOAD"]
        result = run([str(wrapper)], expected=76)
        assert result.stdout == "" and "device state unknown" in result.stderr
        # Exercise the board shell controller using native mocks and isolated
        # test-only lock paths. No production lock or hardware is touched.
        shim = temporary / "bin"
        shim.mkdir()
        (shim / "busybox").write_text('#!/bin/sh\nexec "$@"\n', encoding="utf-8")
        (shim / "busybox").chmod(0o755)
        for mode in ("same", "mixed", "cpu", "kill"):
            case = temporary / mode
            case.mkdir()
            case_lock = case / "device.lock"
            executable = case / "gemmini_linux_check-linux"
            run(flags + [f'-DBB_GEMMINI_LOCK_PATH="{case_lock.as_posix()}"',
                         str(sources[0]), str(sources[2]),
                         str(ROOT / "tests/gemmini_entry_mock.c"), "-o", str(executable)])
            for name in ("gemmini_os_cisc_basic_test-linux", "gemmini_ws_risc_basic_test-linux"):
                shutil.copy2(executable, case / name)
            controller = case / "gemmini_concurrency.sh"
            data = sources[-1].read_text(encoding="utf-8")
            data = data.replace("lock=/tmp/buckyball-gemmini.lock",
                                f"lock={case_lock.as_posix()}")
            data = data.replace('dir="/tmp/gemmini-ownership-',
                                f'dir="{case.as_posix()}/gemmini-ownership-')
            controller.write_text(data, encoding="utf-8")
            environment = os.environ.copy()
            environment["PATH"] = str(shim) + ":" + environment["PATH"]
            if mode == "kill":
                environment["BB_TEST_SLEEP"] = "1"
            result = run(["sh", str(controller), mode], env=environment, timeout=20)
            assert f"OWNERSHIP_CASE PASS {'kill:' if mode == 'kill' else 'mode=' + mode}" in result.stdout
    record = {"result": "PASS_HOST_SOFTWARE_ONLY", "cases": 14,
              "concurrency": {"processes": 6, "transactions": 120, "overlap": 0},
              "elapsed_seconds": round(time.monotonic() - started, 3),
              "hardware_tested": False, "dma_context_isolation_proven": False,
              "board_controller_cases": ["same", "mixed", "cpu", "kill"],
              "board_controller_backend": "native_mock_not_hardware",
              "sources": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sources}, "commands": commands}
    (out / "host.log").write_text("\n".join(transcript), encoding="utf-8")
    (out / "RESULT.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"PASS Gemmini ownership host tests: {record['cases']} cases; hardware_tested=false")


if __name__ == "__main__":
    main()
