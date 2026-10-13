"""按阶段索引定位旧证据；原报告中的逻辑路径保留原文。"""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
INDEX = REPOSITORY / "history/INDEX.json"


def evidence_path(name):
    original = "platforms/arty-a7-toy/evidence/" + name
    for item in json.loads(INDEX.read_text(encoding="utf-8"))["moves"]:
        if original == item["from"] or original.startswith(item["from"] + "/"):
            return REPOSITORY / (item["to"] + original[len(item["from"]):])
    return ROOT / "evidence" / name


if __name__ == "__main__":
    print(evidence_path(sys.argv[1]))
