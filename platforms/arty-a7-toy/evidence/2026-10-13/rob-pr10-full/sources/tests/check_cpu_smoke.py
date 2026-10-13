"""Run a real RV64 program on the complete trimmed chip with AXI RAM models."""

import argparse
import hashlib
import json
import re
import subprocess
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-dir", type=Path, default=ROOT / "build/serial-bound")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "build/cpu-smoke")
    parser.add_argument("--program-elf", type=Path)
    parser.add_argument("--label", default="whole Toy CPU smoke")
    parser.add_argument("--diagnostic-accelerator", action="store_true")
    parser.add_argument("--trace-accelerator", action="store_true")
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    elf = out / "smoke.elf"
    if args.program_elf:
        shutil.copy2(args.program_elf, elf)
    else:
        compile_cpu(elf)
    run_program(args, out, elf)


def compile_cpu(elf):
    subprocess.run(
        [
            "riscv64-unknown-elf-gcc",
            "-nostdlib",
            "-nostartfiles",
            "-march=rv64imafdc_zicsr_zifencei_zfh",
            "-mabi=lp64d",
            "-Wl,--no-relax",
            "-T",
            str(ROOT / "tests/cpu_smoke.ld"),
            str(ROOT / "tests/cpu_smoke.S"),
            "-o",
            str(elf),
        ],
        check=True,
    )


def run_program(args, out, elf):
    assert re.fullmatch(r"[a-zA-Z0-9 _-]+", args.label)
    binary = out / "smoke.bin"
    subprocess.run(
        ["riscv64-unknown-elf-objcopy", "-O", "binary", str(elf), str(binary)],
        check=True,
    )
    (out / "smoke.hex").write_text("\n".join(f"{b:02x}" for b in binary.read_bytes()))
    disassembly = subprocess.check_output(
        ["riscv64-unknown-elf-objdump", "-d", str(elf)], text=True
    )
    (out / "smoke.disasm").write_text(disassembly)
    core = args.core_dir.resolve() / "ToyLinuxChip.sv"
    source = core.read_text()
    header = source.split("module ToyLinuxChip(", 1)[1].split(");", 1)[0]
    signals = []
    direction, width = None, ""
    for part in header.split(","):
        match = re.fullmatch(r"\s*(?:(input|output)\s+)?(\[[^]]+\]\s*)?(\w+)\s*", part)
        assert match, part
        if match[1]:
            direction, width = match[1], match[2] or ""
        signals.append((direction, width, match[3]))
    lines = ["`timescale 1ns/1ps", "module tb;"]
    for direction, width, name in signals:
        if name in ("clock", "reset", "interrupt"):
            lines.append(f"  reg {name}=0;")
        else:
            lines.append(f"  wire {width}{name};")
    lines += [
        "  ToyLinuxChip dut(.*);",
        "  integer cycle_count=0;",
        "  always @(posedge clock) if (!reset) cycle_count<=cycle_count+1;",
        "  always #5 clock=~clock;",
        "  initial begin reset=1; repeat(20) @(negedge clock); reset=0; end",
        "  initial begin repeat(5000000) @(posedge clock); "
        '$fatal(1,"CPU timeout"); end',
    ]
    if args.trace_accelerator:
        acc = "dut.system.tile_prci_domain.element_reset_domain_bbtile.accelerators_0"
        ctrl = acc + ".ballDomain.bbus.balls_0.exCtrl"
        sub = acc + ".frontend.scheduler.subRob"
        a_data = ",".join(f"{ctrl}.mesh.io_a_bits_{i}_0" for i in range(7, -1, -1))
        b_data = ",".join(f"{ctrl}.mesh.io_b_bits_{i}_0" for i in range(7, -1, -1))
        loader = acc + ".memDomain.frontend.memLoader"
        lines += [
            f"always @(posedge clock) if ({loader}.io_cmdReq_valid && {loader}.io_cmdReq_ready) "
            f'$display("LOAD_CMD cycle=%0d addr=%h bank=%0d iter=%0d special=%h", '
            f"cycle_count,{loader}.io_cmdReq_bits_cmd_mem_addr,{loader}.io_cmdReq_bits_cmd_bank_id,"
            f"{loader}.io_cmdReq_bits_cmd_iter,{loader}.io_cmdReq_bits_cmd_special);",
            f"always @(posedge clock) if ({loader}.io_bankWrite_io_req_valid && {loader}.io_bankWrite_io_req_ready) "
            f'$display("LOAD_DATA cycle=%0d bank=%0d row=%0d data=%h", '
            f"cycle_count,{loader}.io_bankWrite_bank_id,{loader}.io_bankWrite_io_req_bits_addr,"
            f"{loader}.io_bankWrite_io_req_bits_data);",
            f"always @(posedge clock) if ({ctrl}.mesh.io_req_valid && {ctrl}.mesh.io_req_ready) "
            f'$display("REQ cycle=%0d state=%0d tag=%0d flush=%0d prop=%0d", '
            f"cycle_count,{ctrl}.state,{ctrl}.mesh.io_req_bits_tag_rob,"
            f"{ctrl}.mesh.io_req_bits_flush,{ctrl}.mesh.io_req_bits_pe_control_propagate);",
            f"always @(posedge clock) if ({ctrl}.mesh.io_a_valid && {ctrl}.mesh.io_a_ready) "
            f'$display("FEED cycle=%0d state=%0d row=%0d a=%h b=%h", '
            f"cycle_count,{ctrl}.state,{ctrl}.feed_row_cnt,{{{a_data}}},{{{b_data}}});",
            f"always @(posedge clock) if ({ctrl}.ctrlIo_bankReadResp_0_valid && {ctrl}.ctrlIo_bankReadResp_0_ready) "
            f'$display("READ0 cycle=%0d state=%0d data=%h", cycle_count,{ctrl}.state,{ctrl}.ctrlIo_bankReadResp_0_bits_data);',
            f"always @(posedge clock) if ({ctrl}.ctrlIo_bankReadResp_1_valid && {ctrl}.ctrlIo_bankReadResp_1_ready) "
            f'$display("READ1 cycle=%0d state=%0d data=%h", cycle_count,{ctrl}.state,{ctrl}.ctrlIo_bankReadResp_1_bits_data);',
            f"always @(posedge clock) if ({ctrl}.ctrlIo_cmdReq_valid && {ctrl}.ctrlIo_cmdReq_ready) "
            f'$display("CMD cycle=%0d sub=%0d special=%h op1=%0d op2=%0d wr=%0d tag=%0d", '
            f"cycle_count,{ctrl}.ctrlIo_cmdReq_bits_cmd_special[3:0],{ctrl}.ctrlIo_cmdReq_bits_cmd_special,"
            f"{ctrl}.ctrlIo_cmdReq_bits_cmd_op1_bank,{ctrl}.ctrlIo_cmdReq_bits_cmd_op2_bank,"
            f"{ctrl}.ctrlIo_cmdReq_bits_cmd_wr_bank,{ctrl}.nextMeshTag);",
            f"always @(posedge clock) if ({ctrl}.ctrlIo_bankWrite_0_req_valid && {ctrl}.ctrlIo_bankWrite_0_req_ready) "
            f'$display("STORE cycle=%0d row=%0d data0=%h data1=%h data2=%h data3=%h", '
            f"cycle_count,{ctrl}.store_row_cnt,{ctrl}.ctrlIo_bankWrite_0_req_bits_data,"
            f"{ctrl}.ctrlIo_bankWrite_1_req_bits_data,{ctrl}.ctrlIo_bankWrite_2_req_bits_data,{ctrl}.ctrlIo_bankWrite_3_req_bits_data);",
            f"always @(posedge clock) if ({sub}.io_write_valid && {sub}.io_write_ready) "
            f'$display("SUB_WRITE cycle=%0d count=%0d rd=%0d wr=%0d state=%0d", '
            f"cycle_count,{sub}.rowCount,{sub}.readPtr,{sub}.writePtr,{sub}.state);",
            f"always @(posedge clock) if ({sub}.io_masterComplete_valid && {sub}.io_masterComplete_ready) "
            f'$display("SUB_MASTER cycle=%0d count=%0d", cycle_count,{sub}.rowCount);',
            f"always @(posedge clock) if ({ctrl}.mesh.io_resp_valid) "
            f'$display("RESP cycle=%0d state=%0d tag=%0d rows=%0d out=%0d collected=%0d data=%h", '
            f"cycle_count,{ctrl}.state,{ctrl}.mesh.io_resp_bits_tag_rob,"
            f"{ctrl}.mesh.io_resp_bits_total_rows,{ctrl}.outBufRows,{ctrl}.outBufCollected,"
            f"{ctrl}.mesh.io_resp_bits_data_0_0);",
        ]
    if args.diagnostic_accelerator:
        acc = "dut.system.tile_prci_domain.element_reset_domain_bbtile.accelerators_0"
        sub = acc + ".frontend.scheduler.subRob"
        probes = {
            "ex_state": acc + ".ballDomain.bbus.balls_0.exCtrl.state",
            "feed_rows": acc + ".ballDomain.bbus.balls_0.exCtrl.feed_row_cnt",
            "read_rows": acc + ".ballDomain.bbus.balls_0.exCtrl.read_row_cnt",
            "out_rows": acc + ".ballDomain.bbus.balls_0.exCtrl.outBufRows",
            "out_collected": acc + ".ballDomain.bbus.balls_0.exCtrl.outBufCollected",
            "total_rows": acc + ".ballDomain.bbus.balls_0.exCtrl.total_rows",
            "req_sent": acc + ".ballDomain.bbus.balls_0.exCtrl.req_sent",
            "mesh_req": acc + ".ballDomain.bbus.balls_0.exCtrl.mesh.req_valid",
            "mesh_counter": acc + ".ballDomain.bbus.balls_0.exCtrl.mesh.fire_counter",
            "matmul_state": acc + ".ballDomain.bbus.balls_0.matmulUnroller.state",
            "max_i": acc + ".ballDomain.bbus.balls_0.matmulUnroller.cfg_max_i",
            "max_j": acc + ".ballDomain.bbus.balls_0.matmulUnroller.cfg_max_j",
            "max_k": acc + ".ballDomain.bbus.balls_0.matmulUnroller.cfg_max_k",
            "iteration": acc + ".ballDomain.bbus.balls_0.matmulUnroller.curIter",
            "sub_state": sub + ".state",
            "sub_rows": sub + ".rowCount",
            "sub_read": sub + ".readPtr",
            "sub_write": sub + ".writePtr",
            "issued0": sub + ".slotIssued_0",
            "issued1": sub + ".slotIssued_1",
            "done0": sub + ".slotDone_0",
            "done1": sub + ".slotDone_1",
            "done2": sub + ".slotDone_2",
            "done3": sub + ".slotDone_3",
        }
        fmt = "DEBUG " + " ".join(f"{key}=%0d" for key in probes)
        values = ",".join(probes.values())
        lines.append(
            f"always @(posedge clock) if (cycle_count==100000 || "
            f'cycle_count==200000) $display("{fmt}",{values});'
        )
        lines.append(
            "initial begin repeat(250000) @(posedge clock); "
            '$fatal(1,"Diagnostic stop"); end'
        )
        ball = acc + ".ballDomain.bbus.balls_0"
        ctrl = ball + ".exCtrl"
        lines.append(
            f"always @(posedge clock) if ({ctrl}.mesh.io_resp_valid && "
            f'{ctrl}.cfg_dataflow) $display("WS_RESPONSE cycle=%0d state=%0d '
            'feed=%0d out=%0d tag=%0d rob=%0d rows=%0d first=%h", '
            f"cycle_count,{ctrl}.state,"
            f"{ctrl}.feed_row_cnt,{ctrl}.outBufRows,"
            f"{ctrl}.mesh.io_resp_bits_tag_rob,{ctrl}.rob_id_reg,"
            f"{ctrl}.mesh.io_resp_bits_total_rows,{ctrl}.mesh.io_resp_bits_data_0_0);"
        )
        lines.append(
            f"always @(posedge clock) if ({ball}.io_cmdReq_valid && "
            f"{ball}.io_cmdReq_ready && !{ball}.io_cmdReq_bits_is_sub) "
            f'$display("COMMAND funct=%0d special=%h", '
            f"{ball}.io_cmdReq_bits_cmd_funct7, {ball}.io_cmdReq_bits_cmd_special);"
        )
    for prefix, data, ids, addr, base, size, extra in (
        ("memory", 128, 4, 32, "80000000", 262144, '.IMAGE("smoke.hex")'),
        (
            "peripherals",
            64,
            2,
            31,
            "60000000",
            4096,
            f'.MONITOR(1), .TEST_LABEL("{args.label}")',
        ),
    ):
        lines.append(
            f"  axi_smoke_memory #(.DATA_BITS({data}), .ID_BITS({ids}), "
            f".ADDR_BITS({addr}), .BASE(32'h{base}), .CAPACITY({size}), "
            f"{extra}) {prefix}_model ("
        )
        ports = [".clock(clock)", ".reset(reset)"]
        for _, _, name in signals:
            if not name.startswith(prefix + "_"):
                continue
            short = name[len(prefix) + 1 :]
            if short.endswith(("_lock", "_cache", "_prot", "_qos")):
                continue
            ports.append(f".{short}({name})")
        lines.append("    " + ",\n    ".join(ports) + "\n  );")
    lines += [
        '  final $display("MEASURE cycles=%0d memory_reads=%0d memory_writes=%0d", '
        "cycle_count, memory_model.read_bursts, memory_model.write_bursts);",
        "endmodule",
    ]
    bench = out / "tb_cpu.sv"
    bench.write_text("\n".join(lines) + "\n")
    obj = out / "obj"
    with (out / "verilator-build.log").open("w") as log:
        subprocess.run(
            [
                "verilator",
                "--binary",
                "--timing",
                "-j",
                "8",
                "-Wno-fatal",
                "-DSYNTHESIS",
                "-DBUCKYBALL_DISABLE_DPI",
                "--top-module",
                "tb",
                "--Mdir",
                str(obj),
                str(core),
                str(args.core_dir.resolve() / "FpgaMemories.sv"),
                str(ROOT / "tests/axi_smoke_memory.sv"),
                str(bench),
            ],
            stdout=log,
            stderr=log,
            check=True,
            timeout=900,
        )
    result = subprocess.run(
        [str(obj / "Vtb")], cwd=out, capture_output=True, text=True, timeout=180
    )
    (out / "simulation.log").write_text(result.stdout + result.stderr)
    print(result.stdout)
    result.check_returncode()
    assert f"PASS {args.label}" in result.stdout
    measure = re.search(
        r"MEASURE cycles=(\d+) memory_reads=(\d+) memory_writes=(\d+)", result.stdout
    )
    assert measure, "Missing cycle and external writeback counters"
    cycles, reads, writes = map(int, measure.groups())
    assert writes > 0, "The test did not exercise dirty writeback to external memory"
    record = {
        "result": "PASS",
        "test_label": args.label,
        "core_rtl_sha256": hashlib.sha256(core.read_bytes()).hexdigest(),
        "test_binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "cycles_including_boot": cycles,
        "memory_read_bursts": reads,
        "memory_write_bursts": writes,
        "linux_boot_tested": False,
    }
    (out / "RESULT.json").write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
