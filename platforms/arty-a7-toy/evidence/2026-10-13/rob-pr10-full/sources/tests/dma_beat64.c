// Exercise the actual CPU/DMA/cache path after adapting DMA beats to eight bytes.
#include "buckyball.h"
#include <bbhw/isa/isa.h>
#include <bbhw/mem/mem.h>

static uint8_t source[8192] __attribute__((aligned(4096)));
static uint8_t destination[8192] __attribute__((aligned(4096)));

int main(void) {
  const int rows = 9;
  const int offsets[] = {0, 1, 3, 7, 4093};
  for (unsigned t = 0; t < sizeof(offsets) / sizeof(offsets[0]); ++t) {
    const int in = offsets[t];
    const int out = offsets[(t + 2) % 5];
    const int stride = (t & 1) + 1;
    for (int i = 0; i < 8192; ++i) {
      source[i] = (uint8_t)(i * 37 + t * 19);
      destination[i] = 0xa5;
    }
    // Four groups exercise splitting and the row skip independently of matrix math.
    bb_mem_alloc(0, 1, 4);
    bb_mvin((uintptr_t)(source + in), 0, rows, stride);
    bb_mvout((uintptr_t)(destination + out), 0, rows, stride);
    bb_fence();
    bb_mem_release(0);
    for (int i = 0; i < 8192; ++i) {
      int relative = i - out;
      int row = relative >= 0 ? relative / (stride * 32) : -1;
      int column = relative >= 0 ? relative % (stride * 32) : -1;
      uint8_t expected = row >= 0 && row < rows && column < 32
          ? source[in + row * stride * 32 + column] : 0xa5;
      if (destination[i] != expected) return (int)t + 1;
    }
  }
  return 0;
}
