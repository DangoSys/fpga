OUTPUT_ARCH(riscv)
ENTRY(_start)
SECTIONS {
  . = 0x10000;
  .text : { *(.text.start) *(.text*) *(.rodata*) }
  ASSERT(. <= 0x11000, "Flash boot code exceeds 4 KiB")
  .data : { *(.data*) *(.sdata*) }
  .bss : { *(.bss*) *(.sbss*) *(COMMON) }
  ASSERT(SIZEOF(.data) == 0 && SIZEOF(.bss) == 0, "Boot ROM must not have writable globals")
  /DISCARD/ : { *(.comment) *(.eh_frame*) *(.riscv.attributes) }
}
