"""Run the complete board flow in isolation with a one-hour hard timeout."""
from datetime import datetime, timedelta, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
TZ=timezone(timedelta(hours=8))
EXPECTED="4c6aacf64660bbbf14b1114e8d5e4439d6a4e1427aaf1f681c6a4f618f2d2779"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, record):
    temp=path.with_suffix(".tmp")
    temp.write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    temp.replace(path)


def worker(out):
    manifest=out/"RUN.json"
    record=json.loads(manifest.read_text())
    now=datetime.now(TZ)
    script=Path(record.get("execution_script",str(ROOT/"board/build_board.tcl")))
    if "execution_script_sha256" in record:
        assert sha(script)==record["execution_script_sha256"]
    command=["timeout","--signal=TERM","--kill-after=15s","3600s",os.environ.get("VIVADO", "vivado"),
             "-mode","batch","-source",str(script),
             "-log",str(out/"vivado.log"),"-journal",str(out/"vivado.jou"),"-tclargs",str(out)]
    if record.get("flash_boot"):
        command.append("flash")
    record.update(status="RUNNING",started_at=now.isoformat(),deadline=(now+timedelta(hours=1)).isoformat(),
                  command=command,worker_pid=os.getpid())
    started=time.monotonic()
    try:
        with (out/"console.log").open("w") as log:
            p=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,
                               stderr=subprocess.STDOUT,start_new_session=True)
            record["timeout_process_pid"]=p.pid
            save(manifest,record)
            code=p.wait()
        record.update(exit_code=code,status="TIMED_OUT" if code in (124,137) else "COMPLETED" if code==0 else "FAILED")
    except Exception as e:
        record.update(status="LAUNCH_FAILED",error=str(e))
    record.update(elapsed_seconds=time.monotonic()-started,finished_at=datetime.now(TZ).isoformat(),
                  core_unchanged=sha(ROOT/"build/serial-bound/ToyLinuxChip.sv")==EXPECTED,
                  bitstream_generated=(out/"toy_a7.bit").is_file())
    save(manifest,record)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--worker",type=Path)
    p.add_argument("--flash",action="store_true",help="Use the validated Flash boot ROM and SPI port")
    args=p.parse_args()
    if args.worker:
        worker(args.worker.resolve());return
    assert sha(ROOT/"build/serial-bound/ToyLinuxChip.sv")==EXPECTED
    if args.flash:
        flash_manifest=json.loads((ROOT/"build/flash-boot/MANIFEST.json").read_text())
        assert flash_manifest["original_core_sha256"]==EXPECTED
        assert sha(ROOT/"build/flash-boot/ToyLinuxChip.sv")==flash_manifest["adapted_core_sha256"]
    for path in (ROOT/"build").glob("board-*/RUN.json"):
        assert json.loads(path.read_text())["status"] not in ("CREATED","RUNNING"),f"Active build: {path}"
    out=ROOT/"build"/("board-"+datetime.now(TZ).strftime("%Y%m%d-%H%M%S"))
    out.mkdir()
    # Snapshot the exact board sources used by this attempt, including failures.
    import shutil
    shutil.copytree(ROOT/"board",out/"inputs/board")
    files={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/"board").rglob("*") if p.is_file()}
    record=dict(status="CREATED",timeout_seconds=3600,termination_grace_seconds=15,
                output_directory=str(out),part="xc7a100tcsg324-1",core_sha256=EXPECTED,
                board_sources=files,core_clock_hz=25000000,uart_baud=1000000,
                vendor_revision="E.0",physical_board_revision="unknown",physical_boot_tested=False,
                flash_boot=args.flash)
    save(out/"RUN.json",record)
    with (out/"launcher.log").open("w") as log:
        p=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),"--worker",str(out)],
                           cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,
                           start_new_session=True,close_fds=True)
    print(json.dumps({"output_directory":str(out),"worker_pid":p.pid,"timeout_seconds":3600}))


if __name__=="__main__":
    main()
