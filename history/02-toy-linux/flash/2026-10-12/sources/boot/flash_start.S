.option norelax
.section .text.start,"ax",@progbits
.globl _start
_start:
  li sp, 0x8ffff000
  la t0, trap
  csrw mtvec, t0
  csrw mie, zero
  li t0, 8
  csrc mstatus, t0
  call flash_main
trap:
  li t0, 0x60000000
  li t1, 0xbad0f100
  sd t1, 0(t0)
1: j 1b
