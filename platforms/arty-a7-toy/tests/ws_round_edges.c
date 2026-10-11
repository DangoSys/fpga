// Independent integer oracle and alternating OS/WS cases on the real CPU.
#include "buckyball.h"
#include <bbhw/isa/isa.h>
#include <bbhw/mem/mem.h>
#include <isa/gemmini.h>

#define DIM 8
static elem_t a[DIM * DIM] __attribute__((aligned(64)));
static elem_t b[DIM * DIM] __attribute__((aligned(64)));
static elem_t d[DIM * DIM] __attribute__((aligned(64)));
static result_t c[DIM * DIM] __attribute__((aligned(64)));
static const int shifts[] = {0, 1, 2, 4, 8, 19, 20, 31};
static const int ties[] = {-41, -40, -39, -25, -24, -23, -9, -8,
                           -7, -3, -2, -1, 0, 1, 2, 3,
                           7, 8, 9, 23, 24, 25, 39, 40, 41};

static int32_t nearest_even(int32_t value, int shift) {
  if (!shift) return value;
  int64_t magnitude = value < 0 ? -(int64_t)value : value;
  int64_t divisor = (int64_t)1 << shift;
  int64_t quotient = magnitude / divisor;
  int64_t remainder = magnitude % divisor;
  if (2 * remainder > divisor ||
      (2 * remainder == divisor && quotient % 2)) quotient++;
  return value < 0 ? -quotient : quotient;
}

int main(void) {
  int run = 0;
  for (unsigned si = 0; si < sizeof(shifts) / sizeof(shifts[0]); si++)
    for (int pattern = 0; pattern < 4; pattern++)
      for (int mode = 0; mode < 2; mode++, run++) {
        for (int r = 0; r < DIM; r++)
          for (int k = 0; k < DIM; k++) {
            int index = r * DIM + k;
            a[index] = pattern == 3 ? -128 : (r == k ? (pattern == 2 ? 4 : 1) : 0);
            b[index] = pattern == 3 ? ((k & 1) ? 127 : -128) : ties[(index + 7 * pattern) % 25];
            d[index] = mode && pattern == 1 ? (index % 7 - 3) : 0;
            c[index] = 0x12345678;
          }
        bb_mem_alloc(0, 1, 1);
        bb_mem_alloc(1, 1, 1);
        bb_mem_alloc(2, 1, 1);
        bb_mem_alloc(3, 1, 4);
        bb_mvin((uintptr_t)b, 0, DIM, 1);
        bb_mvin((uintptr_t)a, 1, DIM, 1);
        bb_mvin((uintptr_t)d, 2, DIM, 1);
        bb_gemmini_config(mode, 0, 0, 0, shifts[si]);
        bb_gemmini_preload(mode ? 0 : 1, 3, DIM, 0, 0);
        bb_gemmini_compute_preloaded(1, mode ? 2 : 0, 3, DIM, 0, 0, 0);
        bb_mvout((uintptr_t)c, 3, DIM, 1);
        bb_fence();
        for (int r = 0; r < DIM; r++)
          for (int col = 0; col < DIM; col++) {
            int32_t sum = d[r * DIM + col];
            for (int k = 0; k < DIM; k++)
              sum += (int32_t)a[r * DIM + k] * b[k * DIM + col];
            if (c[r * DIM + col] != nearest_even(sum, shifts[si])) return run + 1;
          }
        for (int bank = 0; bank < 4; bank++) bb_mem_release(bank);
      }
  return 0;
}
