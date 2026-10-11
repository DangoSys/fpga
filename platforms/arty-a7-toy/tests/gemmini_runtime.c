// Bare-metal test adapter only. Test C bodies, ISA headers and matrix reference
// functions come unchanged from the pinned upstream repository.
#include <stddef.h>
#include <stdint.h>

static uint32_t bank_columns[16];

void bb_dma_bank_set_cols(uint32_t bank, uint32_t columns) {
  if (bank >= 16) {
    *(volatile uint64_t *)0x60000000 = 0xbad0ee01;
    for (;;) {}
  }
  bank_columns[bank] = columns;
}

uint32_t bb_dma_bank_cols(uint32_t bank) {
  return bank_columns[bank];
}

// Console formatting is irrelevant to the return-value checks. Progress and
// pass/fail events are emitted explicitly by the test runner over MMIO.
int printf(const char *format, ...) {
  (void)format;
  return 0;
}

void *memset(void *destination, int value, size_t size) {
  unsigned char *bytes = destination;
  for (size_t i = 0; i < size; ++i) bytes[i] = (unsigned char)value;
  return destination;
}
