"""Guard the full-feature requirement and the original software-visible ISA."""

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "resolve_config", ROOT / "scripts/resolve_config.py"
)
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)


class OriginalPebbleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        resolver.resolve()
        cls.config = json.loads((ROOT / "build/original-pebble.json").read_text())

    def test_unmodified_sources(self):
        manifest = json.loads((ROOT / "UPSTREAM_MANIFEST.json").read_text())
        for name, expected in manifest["files"].items():
            with self.subTest(source=name):
                actual = hashlib.sha256(
                    (ROOT / "upstream" / name).read_bytes()
                ).hexdigest()
                self.assertEqual(actual, expected)

    def test_linux_cpu_features_and_cache_capacities(self):
        cpu = self.config["cpu"]
        for key in ("useVM", "useZba", "useZbb", "useZbs"):
            self.assertTrue(cpu[key], key)
        self.assertEqual(cpu["fpu"], {"enable": True, "minFLen": 16, "fLen": 64})
        self.assertTrue(cpu["btb"]["enable"])
        self.assertEqual(cpu["mulDiv"]["mulUnroll"], 8)
        self.assertEqual(cpu["icache"]["nSets"] * cpu["icache"]["nWays"] * 64, 32768)
        self.assertEqual(cpu["dcache"]["nSets"] * cpu["dcache"]["nWays"] * 64, 8192)
        tile = self.config["accelerator"]["tile"]
        self.assertEqual(
            (tile["xLen"], tile["pgLevels"], tile["vaddrBits"]), (64, 3, 39)
        )

    def test_original_opcode_abi(self):
        domain = self.config["accelerator"]["ballDomain"]
        names = [mapping["ballName"] for mapping in domain["ballIdMappings"]]
        self.assertEqual(
            names,
            [
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
            ],
        )
        self.assertEqual(
            [mapping["ballId"] for mapping in domain["ballIdMappings"]], list(range(10))
        )
        self.assertEqual(
            {item["funct7"]: names[item["bid"]] for item in domain["ballISA"]},
            {
                49: "TransposeBall",
                65: "SMatMulBall",
                17: "SMatMulBall",
                48: "Im2colBall",
                51: "ToInt8Ball",
                67: "ToInt8Ball",
                68: "Int2FpBall",
                66: "LutBall",
                50: "MaxPoolBall",
                69: "Int8AddBall",
                70: "Int8AddBall",
                71: "Int8MulBall",
                72: "MatAddBall",
            },
        )

    def test_original_memory_and_scheduling(self):
        accelerator = self.config["accelerator"]
        mem = accelerator["memDomain"]
        self.assertEqual(
            (mem["bankNum"], mem["bankEntries"], mem["bankWidth"]), (24, 64, 128)
        )
        self.assertEqual(mem["virtualBankCount"], 24)
        self.assertEqual(mem["memAddrLen"], 39)
        self.assertEqual((mem["dma_n_xacts"], mem["max_in_flight_mem_reqs"]), (8, 16))
        self.assertTrue(accelerator["frontend"]["rs_out_of_order_response"])
        self.assertEqual(accelerator["frontend"]["iter_len"], 34)
        self.assertEqual(accelerator["gpDomain"]["vLen"], 1024)


if __name__ == "__main__":
    unittest.main()
