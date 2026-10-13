"""Export software instruction definitions from the actual elaborated profile."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
profile = json.loads((ROOT / "build/serial-raw/ToyLinuxChip.profile.json").read_text())
original = json.loads((ROOT / "build/original-toy.json").read_text())
entries = original["accelerator"]["ballDomain"]["ballISA"]
supported = set(profile["ball_funct7"])
retained = [e for e in entries if e["funct7"] in supported]
assert {e["funct7"] for e in retained} == supported
assert all(e["bid"] in profile["ball_ids"] for e in retained)
out = ROOT / "build/software"
out.mkdir(parents=True, exist_ok=True)
header = ["#ifndef TOY_FPGA_BALL_ISA_H", "#define TOY_FPGA_BALL_ISA_H"]
header += [f"#define BB_FUNC7_{e['mnemonic']} {e['funct7']}" for e in retained]
header += ["#endif", ""]
(out / "ballISA.h").write_text("\n".join(header), encoding="utf-8", newline="\n")
(out / "CAPABILITIES.json").write_text(
    json.dumps(
        {
            "balls": profile["ball_names"],
            "gemmini_dimension": profile["gemmini_rows"],
            "physical_bank_count": profile["bank_count"],
            "virtual_bank_count": profile["virtual_bank_count"],
            "bank_entries": profile["bank_rows"],
            "bank_width": profile["bank_width"],
            "l2_present": False,
            "coherence_manager": profile["coherence_manager"],
            "ball_isa": retained,
            "removed_ball_isa": [e for e in entries if e["funct7"] not in supported],
            "mvin_mmio_supported": profile["accelerator_mmio_scale_pool"],
            "automatic_software_emulation": False,
            "unsupported_rocc_instruction_trap_guaranteed": False,
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
    newline="\n",
)
(out / "params.h").write_text(
    f"#define BANK_WIDTH {profile['bank_width']}\n"
    f"#define VIRTUAL_BANK_NUM {profile['virtual_bank_count']}\n"
    f"#define PHYSICAL_BANK_NUM {profile['bank_count']}\n"
    f"#define BANK_ENTRIES {profile['bank_rows']}\n"
    f"#define GEMMINI_DIM {profile['gemmini_rows']}\n",
    encoding="utf-8",
    newline="\n",
)
print(f"Exported {len(retained)} Ball opcodes from the elaborated profile")
