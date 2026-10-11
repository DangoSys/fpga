OUTPUT_ARCH(riscv)
ENTRY(_start)
SECTIONS {
  . = 0x80000000;
  .text : { *(.text.init) *(.text*) }
  . = ALIGN(16);
  .data : { *(.data*) }
  .bss : { *(.bss*) *(COMMON) }
  /DISCARD/ : { *(.comment) *(.riscv.attributes) }
}
