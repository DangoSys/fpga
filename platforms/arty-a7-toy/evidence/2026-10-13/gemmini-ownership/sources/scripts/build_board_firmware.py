"""Rebuild the pinned OpenSBI payload for the board's actual CLINT frequency.

Uses the existing pinned Linux+BusyBox image unchanged. Copies OpenSBI and its
platform into this isolated candidate, never modifies the earlier software.
"""
import hashlib
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT
OUT=ROOT/"build/board-software"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    global BASE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--software-base",type=Path,default=ROOT,
                        help="Root containing build/software from software/build.sh")
    parser.add_argument("--cross-compile",default="riscv64-linux-gnu-")
    args=parser.parse_args()
    BASE=args.software_base.resolve()
    OUT.mkdir(parents=True,exist_ok=True)
    source=BASE/"build/software/bb-tests/thirdparty/opensbi"
    platform=BASE/"build/software/bb-tests/workloads/lib/kernel/opensbi-platform"
    image=BASE/"build/software/kernel-build/linux/arch/riscv/boot/Image"
    image_sha=sha(image)
    for original,target in ((source,OUT/"opensbi-src"),(platform,OUT/"platform")):
        if not target.exists():
            shutil.copytree(original,target,ignore=shutil.ignore_patterns(".git","build"))
    original=(platform/"buckyball/platform.c").read_text()
    assert original.count("#define BUCKYBALL_MTIMER_FREQ 1000000")==1
    adapted=original.replace("#define BUCKYBALL_MTIMER_FREQ 1000000","#define BUCKYBALL_MTIMER_FREQ 500000")
    old="""  if (fdt_open_into(src, dst, size) == 0)
    return BUCKYBALL_DTB_STAGING_ADDR;"""
    new="""  if (fdt_open_into(src, dst, size + 512) == 0) {
    int cpus = fdt_path_offset(dst, "/cpus");
    if (cpus >= 0) {
      if (fdt_setprop_u32(dst, cpus, "timebase-frequency",
                          BUCKYBALL_MTIMER_FREQ) != 0)
        return 0;
      int cpu;
      fdt_for_each_subnode(cpu, dst, cpus) {
        fdt_setprop_u32(dst, cpu, "timebase-frequency", BUCKYBALL_MTIMER_FREQ);
        fdt_setprop_u32(dst, cpu, "clock-frequency", 25000000);
      }
    }
    return BUCKYBALL_DTB_STAGING_ADDR;
  }"""
    assert adapted.count(old)==1
    adapted=adapted.replace(old,new)
    (OUT/"platform/buckyball/platform.c").write_text(adapted)
    shutil.copy2(image,OUT/"Image")
    command=["make","-C",str(OUT/"opensbi-src"),"-j8","CROSS_COMPILE="+args.cross_compile,
             "PLATFORM_DIR="+str(OUT/"platform"),"PLATFORM=buckyball","O="+str(OUT/"opensbi-build"),
             "FW_PAYLOAD_PATH="+str(OUT/"Image"),"BUCKYBALL_VISIBLE_HART_COUNT=1",
             "BUCKYBALL_TOTAL_HART_COUNT=1","BUCKYBALL_HIDDEN_HART_BASE=1"]
    with (OUT/"build.log").open("w") as log:
        subprocess.run(command,stdout=log,stderr=log,check=True,timeout=900)
    payload=OUT/"opensbi-build/platform/buckyball/firmware/fw_payload.bin"
    shutil.copy2(payload,OUT/"fw_payload.bin")
    assert sha(image)==image_sha==sha(OUT/"Image")
    record=dict(result="PASS_BUILD",payload_sha256=sha(payload),payload_bytes=payload.stat().st_size,
                linux_image_sha256=image_sha,linux_image_unchanged=True,clint_frequency_hz=500000,
                core_frequency_hz=25000000,console_base="0x60020000",memory_bytes=268435456,
                original_platform_sha256=sha(platform/"buckyball/platform.c"),
                adapted_platform_sha256=sha(OUT/"platform/buckyball/platform.c"),
                original_payload_sha256=sha(BASE/"build/software/kernel-build/opensbi/platform/buckyball/firmware/fw_payload.bin"),
                boot_tested=False,command=command)
    (OUT/"RESULT.json").write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps(record,indent=2))


if __name__=="__main__":
    main()
