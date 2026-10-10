"""Read the pinned Pebble TOMLs; emit inputs to the upstream parameter readers."""

import json
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "upstream"


def read(path):
    return tomllib.loads(path.read_text(encoding="utf-8"))


def resolve():
    tile_path = UPSTREAM / "examples/chips/pebble/configs/designs/tiles/default.toml"
    tile = read(tile_path)
    assert len(tile["cores"]) == 1
    assert not tile["privateDCache"]["enable"]
    assert not tile["sharedMem"]["enable"]
    core_path = (tile_path.parent / tile["cores"][0]["include"]).resolve()
    core = read(core_path)
    cpu_path = core_path.parent / core["cpu"]
    cpu_ref = read(cpu_path)
    assert cpu_ref["kind"] == "rocket"
    cpu = read(cpu_path.parent / cpu_ref["config"])
    mem = read(core_path.parent / core["memdomain"])
    front = read(core_path.parent / core["frontend"])
    domain_path = core_path.parent / core["balldomain"]
    balls = read(domain_path)
    for mapping in balls["ballIdMappings"]:
        config = (domain_path.parent / mapping["config"]).resolve()
        assert config.is_file() and config.is_relative_to(UPSTREAM.resolve())
        mapping["config"] = [config.relative_to(UPSTREAM.resolve()).as_posix()]
    shared = tile["sharedMem"]
    frontend_keys = {
        "robEntries": "rob_entries",
        "rsOutOfOrderResponse": "rs_out_of_order_response",
        "bankIdLen": "bank_id_len",
        "vbankIdUpperBound": "vbank_id_upper_bound",
        "sharedBankIdBase": "shared_bank_id_base",
        "iterLen": "iter_len",
        "subRobEnable": "sub_rob_enable",
        "subRobDepth": "sub_rob_depth",
    }
    result = {
        "cpu": cpu,
        "accelerator": {
            "tile": {
                k: tile[k]
                for k in (
                    "coreDataBytes",
                    "xLen",
                    "vaddrBits",
                    "paddrBits",
                    "pgIdxBits",
                    "pgLevels",
                    "nPMPs",
                )
            },
            "frontend": {frontend_keys[k]: v for k, v in front.items()},
            "gpDomain": read(core_path.parent / core["gpdomain"]),
            "ballDomain": balls,
            "sim": {"diffTest": False},
            "memDomain": {
                "bankNum": mem["bank"]["num"],
                "bankWidth": mem["bank"]["width"],
                "bankEntries": mem["bank"]["entries"],
                "bankMaskLen": mem["bank"]["maskLen"],
                # bbdev 2_parameter_derivation.py: explicit shared override,
                # otherwise the largest private-bank count in this tile.
                "virtualBankCount": shared.get("virtualBankCount", mem["bank"]["num"]),
                "sharedEnable": shared["enable"],
                "sharedEntries": shared["entries"],
                "sharedBankNum": 0,
                "sharedInputChannels": shared["inputChannels"],
                "sharedDefaultGroupCount": shared["defaultGroupCount"],
                "nCores": 1,
                "tlb_size": mem["tlb"]["size"],
                "dma_n_xacts": mem["dma"]["nXacts"],
                "dma_burst_maxbytes": mem["dma"]["burstMaxBytes"],
                "bankChannel": mem["bank"]["channel"],
                "max_in_flight_mem_reqs": mem["dma"]["maxInFlightMemReqs"],
                "dma_buswidth": mem["dma"]["busWidth"],
                "memAddrLen": mem["mem"]["addrLen"],
                "tmaReadChannel": mem["tma"]["readChannel"],
                "tmaWriteChannel": mem["tma"]["writeChannel"],
                **{"mmio" + k[0].upper() + k[1:]: v for k, v in mem["mmio"].items()},
            },
        },
    }
    output = ROOT / "build/original-pebble.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        f"Original Pebble: VM={cpu['useVM']}, FPU={cpu['fpu']}, "
        f"Balls={balls['ballNum']}, banks={mem['bank']}"
    )


if __name__ == "__main__":
    resolve()
