"""Summarize measured OOC resource use; never equate it with routed success."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPACITY = {"LUT": 63400, "FF": 126800, "BRAM_tiles": 135, "DSP": 240}
LABELS = {
    "Slice LUTs*": "LUT",
    "Slice Registers": "FF",
    "Block RAM Tile": "BRAM_tiles",
    "DSPs": "DSP",
}


def read_utilization(path):
    found = {}
    for line in path.read_text().splitlines():
        fields = [field.strip() for field in line.split("|")]
        if len(fields) > 6 and fields[1] in LABELS:
            resource = LABELS[fields[1]]
            found[resource] = float(fields[2].replace(",", ""))
            assert float(fields[5].replace(",", "")) == CAPACITY[resource]
    assert found.keys() == CAPACITY.keys(), f"Incomplete report: {path}"
    return found


def main():
    core = read_utilization(ROOT / "build/synth/utilization.rpt")
    mig = read_utilization(ROOT / "build/mig/utilization.rpt")
    over = {
        resource: used for resource, used in core.items() if used > CAPACITY[resource]
    }
    result = {
        "part": "xc7a100tcsg324-1",
        "stage": "out_of_context_synthesis",
        "core_rtl_sha256": hashlib.sha256(
            (ROOT / "generated/PebbleLinuxChip.sv").read_bytes()
        ).hexdigest(),
        "capacity": CAPACITY,
        "full_core": core,
        "official_mig": mig,
        "core_exceeds_capacity": over,
        "independent_ooc_sum_estimate": {key: core[key] + mig[key] for key in CAPACITY},
        "routed": False,
        "linux_boot_tested": False,
        "board_release_ready": False,
    }
    output = ROOT / "build/RESOURCE_FIT.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if over:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
