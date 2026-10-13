.option norvc
.option norelax
.section .text.init,"ax",@progbits
.globl _start
_start:
  la t0, trap_handler
  csrw mtvec, t0
  csrw medeleg, zero
  csrw mie, zero
  li s1, 0
  li t0, 0x60030000
  sd zero, 0(t0)
  fence iorw, iorw
  ld t1, 0(t0)
  fence iorw, iorw
  # Record synchronous traps without assuming the cache supplies them.
  li t0, 0x60000000
  li t1, 0x74000000
  or t1, t1, s1
  sd t1, 0(t0)
  li t0, 0x60000000
  li t1, 0x600d600d
  sd t1, 0(t0)
1: j 1b

.balign 4
trap_handler:
  csrr a0, mcause
  li a2, 5
  beq a0, a2, check_address
  li a2, 7
  bne a0, a2, fail
check_address:
  csrr a1, mtval
  beqz a1, resume
  li a2, 0x60030000
  bne a1, a2, fail
resume:
  addi s1, s1, 1
  csrr a0, mepc
  addi a0, a0, 4
  csrw mepc, a0
  mret

fail:
  li t0, 0x60000000
  li t1, 0xbad00007
  sd t1, 0(t0)
2: j 2b
