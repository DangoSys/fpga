.option norvc
.option norelax
.section .text.init,"ax",@progbits
.globl _start
_start:
  la t0, trap_handler
  csrw mtvec, t0
  csrw medeleg, zero
  csrw mie, zero
  li s10, 0
  li s11, 0
  li gp, 1
  li t0, 0x60000000
  li t1, 0xb007
  sd t1, 0(t0)

  # EBREAK remains an ordinary architectural breakpoint exception.
  li s10, 3
  ebreak
  li t0, 1
  bne s11, t0, fail
  # Debug CSR access is illegal when useDebug=false.
  li s10, 2
  csrr t0, 0x7b0
  li t0, 2
  bne s11, t0, fail
  # The removed auxiliary RAM must fault rather than hang or alias DDR.
  li s10, 5
  li t0, 0x08000000
  ld t1, 0(t0)
  li t0, 3
  bne s11, t0, fail
  li s10, 0

  li gp, 2
  csrr s0, mcycle
  csrr s1, minstret
  li t0, 256
1: addi t0, t0, -1
  bnez t0, 1b
  csrr t0, mcycle
  bgeu s0, t0, fail
  csrr t0, minstret
  bgeu s1, t0, fail

  li gp, 3
  li t0, 0x0200bff8
  ld s0, 0(t0)
  li t1, 256
2: addi t1, t1, -1
  bnez t1, 2b
  ld t1, 0(t0)
  bgeu s0, t1, fail
  li t0, 0x0c000004
  li t1, 1
  sw t1, 0(t0)
  lw t2, 0(t0)
  bne t1, t2, fail

  li gp, 4
  li t0, 0x6000
  csrs mstatus, t0
  li t0, 3
  fcvt.d.w f0, t0
  fadd.d f1, f0, f0
  fcvt.w.d t1, f1, rtz
  li t2, 6
  bne t1, t2, fail
  fcvt.s.w f0, t0
  fmul.s f1, f0, f0
  fcvt.w.s t1, f1, rtz
  li t2, 9
  bne t1, t2, fail
  fcvt.h.w f0, t0
  fadd.h f1, f0, f0
  fcvt.w.h t1, f1, rtz
  li t2, 6
  bne t1, t2, fail
  la t0, datum
  fsd f1, 8(t0)
  fld f2, 8(t0)
  fmv.x.d t1, f1
  fmv.x.d t2, f2
  bne t1, t2, fail

  li gp, 5
  la t0, datum
  li t1, 35
  sd t1, 0(t0)
  li t2, 7
  amoadd.d t3, t2, (t0)
  bne t1, t3, fail
  ld t3, 0(t0)
  li t1, 42
  bne t1, t3, fail
  mul t3, t1, t2
  div t3, t3, t2
  bne t1, t3, fail

  # Indirect calls and returns at 512-byte spacing force I-cache conflicts.
  # Each of 64 stubs is called three times, including with no BTB/RAS.
  li gp, 9
  li s2, 0
  li s3, 3
icache_pass:
  la s0, instruction_stubs
  li s1, 64
icache_call:
  jalr ra, s0, 0
  addi s0, s0, 512
  addi s1, s1, -1
  bnez s1, icache_call
  addi s3, s3, -1
  bnez s3, icache_pass
  li t0, 192
  bne s2, t0, fail

  # 64 KiB of dirty lines exceeds both L1 and the compact 32 KiB L2.
  # Write/read both directions and repeat with a changed data pattern.
  li gp, 10
  li s3, 2
cache_pass:
  la s0, cache_data
  li s1, 8192
  li s2, 0
cache_fill:
  xor t0, s2, s3
  sd t0, 0(s0)
  addi s0, s0, 8
  addi s2, s2, 1
  addi s1, s1, -1
  bnez s1, cache_fill
  fence rw, rw
  li s1, 8192
cache_read_reverse:
  addi s0, s0, -8
  addi s2, s2, -1
  ld t0, 0(s0)
  xor t1, s2, s3
  bne t0, t1, fail
  addi s1, s1, -1
  bnez s1, cache_read_reverse
  li s1, 8192
cache_read_forward:
  ld t0, 0(s0)
  xor t1, s2, s3
  bne t0, t1, fail
  addi s0, s0, 8
  addi s2, s2, 1
  addi s1, s1, -1
  bnez s1, cache_read_forward
  addi s3, s3, -1
  bnez s3, cache_pass

  li gp, 6
  # Three identity 1 GiB mappings plus a virtual DDR alias at 0xc0000000.
  la t0, root_page
  li t1, 0xcf
  sd t1, 0(t0)
  li t1, 0x100000cf
  sd t1, 8(t0)
  li t1, 0x200000cf
  sd t1, 16(t0)
  sd t1, 24(t0)
  fence rw, rw
  li t1, -1
  csrw pmpaddr0, t1
  li t1, 0xf
  csrw pmpcfg0, t1
  li t1, 7
  csrw mcounteren, t1
  srli t0, t0, 12
  li t1, 0x8000000000000000
  or t0, t0, t1
  csrw satp, t0
  sfence.vma
  la t0, supervisor
  csrw mepc, t0
  li t0, 0x1800
  csrc mstatus, t0
  li t0, 0x800
  csrs mstatus, t0
  mret

supervisor:
  li gp, 7
  la t0, datum
  li t1, 0x40000000
  add t0, t0, t1
  ld t2, 0(t0)
  li t3, 42
  bne t2, t3, fail
  li t2, 43
  sd t2, 0(t0)
  la t0, datum
  ld t3, 0(t0)
  bne t2, t3, fail
  csrr t0, cycle
  beqz t0, fail
  li gp, 8
  li s10, 9
  ecall
  j fail

trap_handler:
  csrr t0, mcause
  bne t0, s10, fail
  addi s11, s11, 1
  li t1, 9
  beq t0, t1, passed
  csrr t0, mepc
  addi t0, t0, 4
  csrw mepc, t0
  mret

passed:
  li t0, 4
  bne s11, t0, fail
  li t0, 0x60000000
  li t1, 0x600d600d
  sd t1, 0(t0)
3: j 3b

fail:
  li t0, 0x60000000
  li t1, 0xbad00000
  or t1, t1, gp
  sd t1, 0(t0)
4: j 4b

.balign 512
instruction_stubs:
.rept 64
  addi s2, s2, 1
  ret
  .space 504
.endr

.section .data,"aw",@progbits
.balign 16
datum:
  .dword 0, 0
.balign 4096
root_page:
  .zero 4096
.balign 4096
cache_data:
  .zero 65536
