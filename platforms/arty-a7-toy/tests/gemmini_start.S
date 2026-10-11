.option norvc
.option norelax
.section .text.init,"ax",@progbits
.globl _start
_start:
  li sp, 0x8003fff0
  la t0, trap_failure
  csrw mtvec, t0
  csrw mie, zero
  csrw medeleg, zero
  li t0, 0x1e000
  csrs mstatus, t0
  call main
  li t0, 0x60000000
  li t1, 0x600d600d
  beqz a0, passed
  li t1, 0xbad00000
  or t1, t1, a0
passed:
  sd t1, 0(t0)
1: j 1b
trap_failure:
  csrr t2, mcause
  li t0, 0x60000000
  li t1, 0xbad0f000
  or t1, t1, t2
  sd t1, 0(t0)
2: j 2b
