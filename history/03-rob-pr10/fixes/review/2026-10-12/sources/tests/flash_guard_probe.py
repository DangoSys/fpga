"""隔离进程内替代编程边界，确保测试永不访问串口或启动 Vivado。"""

import json
from pathlib import Path
import runpy
import sys
import types


class ProgrammingBoundary(Exception):
    pass


class OfflineObserver:
    def __init__(self, *args, **kwargs):
        raise ProgrammingBoundary("Guard accepted the valid image")


fake = types.ModuleType("observe_flash_boot")
fake.Observer = OfflineObserver
sys.modules["observe_flash_boot"] = fake
script, bit, payload, mcs, out, expected = sys.argv[1:]
sys.argv = [script, "--bitstream", bit, "--payload", payload, "--mcs", mcs,
            "--part", "mt25ql128-spi-x1_x2_x4", "--port", "OFFLINE_NO_DEVICE",
            "--vivado", "OFFLINE_NO_VIVADO", "--out", out]
try:
    runpy.run_path(script, run_name="__main__")
except ValueError as error:
    if expected != "reject":
        raise
    print("PASS INVALID_IMAGE_BLOCKED", str(error))
except ProgrammingBoundary:
    if expected != "accept":
        raise
    print("PASS VALID_IMAGE_REACHED_OFFLINE_BOUNDARY")
else:
    raise RuntimeError("Missing verification boundary")
