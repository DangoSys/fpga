"""Repeat the unchanged CPU/Gemmini/loop/DMA oracles through board RTL."""
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,str(ROOT/"scripts/check_board.py")],check=True,timeout=180)
records={}
for name in ("cpu","gemmini","loop","dma"):
    subprocess.run([sys.executable,str(ROOT/"scripts/check_board_cpu.py"),"--test",name],check=True,timeout=1000)
    records[name]=json.loads((ROOT/("build/board-"+name)/"RESULT.json").read_text())
(ROOT/"build/BOARD_REGRESSION.json").write_text(json.dumps(dict(result="PASS",tests=records),indent=2)+"\n")
print("PASS BOARD_REGRESSION CPU/Gemmini/loop/DMA")
