"""验证普通模式与 python -O 下四项预打包镜像校验均有效。"""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / "build/flash-guard-check"
    out.mkdir(parents=True, exist_ok=True)
    cases = []
    for optimized in [False, True]:
        for field in [None, "result", "bitstream_sha256", "packed_payload_sha256", "flash_image_sha256"]:
            with tempfile.TemporaryDirectory(dir=out) as directory:
                work = Path(directory)
                bit, payload, mcs = [work / name for name in ["chip.bit", "payload.bin", "image.mcs"]]
                for path in [bit, payload, mcs]:
                    path.write_bytes(path.name.encode())
                sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
                record = {"result": "PASS_VIVADO_FLASH_PACK", "bitstream_sha256": sha(bit),
                          "packed_payload_sha256": sha(payload), "flash_image_sha256": sha(mcs)}
                if field:
                    record[field] = "FAILED" if field == "result" else "0" * 64
                mcs.with_suffix(".mcs.json").write_text(json.dumps(record))
                expected = "reject" if field else "accept"
                command = [sys.executable] + (["-O"] if optimized else [])
                command += [str(ROOT / "tests/flash_guard_probe.py"), str(ROOT / "host/flash.py"),
                            str(bit), str(payload), str(mcs), str(work / "run"), expected]
                result = subprocess.run(command, capture_output=True, text=True, timeout=20)
                name = f"{'optimized' if optimized else 'normal'}-{field or 'valid'}"
                (out / f"{name}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
                result.check_returncode()
                if ("PASS INVALID_IMAGE_BLOCKED" if field else "PASS VALID_IMAGE_REACHED_OFFLINE_BOUNDARY") not in result.stdout:
                    raise ValueError("Missing guard oracle")
                cases.append({"optimized": optimized, "field": field or "valid", "result": "PASS"})
    (out / "RESULT.json").write_text(json.dumps({"result": "PASS_FLASH_GUARDS_NORMAL_AND_OPTIMIZED",
                                               "physical_hardware_tested": False, "cases": cases}, indent=2) + "\n")
    print(f"PASS Flash image guards: {len(cases)} normal/-O tamper/control cases; no hardware")


if __name__ == "__main__":
    main()
