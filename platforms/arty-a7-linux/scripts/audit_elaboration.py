"""Verify required features in Chisel output (not a functional boot test)."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
generated = ROOT / "generated"
rtl = (generated / "PebbleLinuxChip.sv").read_text()
modules = set(re.findall(r"^module\s+(\w+)", rtl, re.MULTILINE))
required = {
    "PTW",
    "FPU",
    "InclusiveCache",
    "TransposeBall",
    "SMatMulBall",
    "Im2colBall",
    "ToInt8Ball",
    "Int2FpBall",
    "LutBall",
    "MaxPoolBall",
    "Int8AddBall",
    "Int8MulBall",
    "MatAddBall",
}
assert required <= modules, f"Missing modules: {required - modules}"
dts = (generated / "PebbleLinuxChip.dts").read_text()
for property_text in (
    'mmu-type = "riscv,sv39"',
    "d-cache-size = <8192>",
    "i-cache-size = <32768>",
    "cache-size = <524288>",
    "timebase-frequency = <1000000>",
):
    assert property_text in dts, property_text
isa = re.search(r'riscv,isa = "([^"]+)"', dts).group(1)
assert isa.startswith("rv64imafdc"), isa
assert all(extension in isa.split("_") for extension in ("zfh", "zba", "zbb", "zbs"))
scratch = re.search(r"memory@8000000\s*\{(.*?)\};", dts, re.DOTALL).group(1)
assert 'status = "disabled"' in scratch, "Scratchpad must not become Linux main RAM"
mapping = json.loads((generated / "PebbleLinuxChip.memmap.json").read_text())["mapping"]
regions = {region["base"][0]: region["size"][0] for region in mapping}
assert regions[0x08000000] == 65536
assert regions[0x80000000] == 256 * 1024 * 1024
assert 0x02000000 in regions and 0x0C000000 in regions
l2 = json.loads((generated / "PebbleLinuxChip.l2.json").read_text())
capacity = sum(
    (1 << len(bank["setBits"])) * bank["ways"] * bank["blockBytes"]
    for bank in l2["banks"]
)
assert capacity == 512 * 1024
record = {
    "result": "PASS_STATIC_ELABORATION_AUDIT",
    "functional_boot_test": False,
    "isa": isa,
    "l2_bytes": capacity,
    "required_modules": sorted(required),
    "memory_regions": {hex(base): size for base, size in regions.items()},
}
(generated / "FEATURE_AUDIT.json").write_text(json.dumps(record, indent=2) + "\n")
print(
    "PASS: Sv39/FPU/ISA, ten operators, full L2/scratchpad, CLINT/PLIC and DDR aperture"
)
