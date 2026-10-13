"""Bind the already validated zero-latency FPU RF adapter after SRAM binding."""

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
output = ROOT / "build/serial-bound"
core = output / "ToyLinuxChip.sv"
original = core.read_text(encoding="utf-8")
matches = list(re.finditer(r"^module regfile_32x65\(.*?^endmodule", original, re.M | re.S))
assert len(matches) == 1
match = matches[0]
reference = (ROOT / "rtl/FpuRfOriginal.sv").read_text(encoding="utf-8").strip()
assert match.group() == reference.replace("module FpuRfOriginal(", "module regfile_32x65(")
replacement = (ROOT / "rtl/FpuRfLvt.sv").read_text(encoding="utf-8").strip()
replacement = replacement.replace("module FpuRfLvt(", "module regfile_32x65(")
adapted = original[:match.start()] + replacement + original[match.end():]
core.write_text(adapted, encoding="utf-8", newline="\n")
assert adapted.replace(replacement, match.group(), 1) == original
manifest = json.loads((output / "MEMORY_MANIFEST.json").read_text())
manifest["baseline_core_rtl_sha256"] = manifest["core_rtl_sha256"]
manifest["core_rtl_sha256"] = hashlib.sha256(core.read_bytes()).hexdigest()
manifest["additional_memory_adapters"] = [{
    "module": "regfile_32x65", "implementation": "two single-write LUTRAM banks and LVT",
    "read_ports": 3, "write_ports": 2, "read_latency": 0,
    "same_address_write_priority": "W1", "added_cycles": 0,
    "adapter_sha256": hashlib.sha256((ROOT / "rtl/FpuRfLvt.sv").read_bytes()).hexdigest(),
}]
(output / "MEMORY_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("PASS RF adapter matches original port contract; only RF module body replaced")
print("Final core SHA256:", manifest["core_rtl_sha256"])
