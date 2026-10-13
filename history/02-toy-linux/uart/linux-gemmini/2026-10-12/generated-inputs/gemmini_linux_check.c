// Linux workload for the actual 8x8 profile; use the pinned upstream ISA and DMA library.
#define _GNU_SOURCE
#include "buckyball.h"
#include <bbhw/isa/isa.h>
#include <bbhw/mem/mem.h>
#include <isa/gemmini.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

#if GEMMINI_DIM != 8 || BANK_WIDTH != 64
#error This workload requires the emitted Toy FPGA 8x8 / 64-bit bank profile.
#endif

enum { TILE = 8, MAX_DIM = 24 };
static elem_t tile_a[TILE * TILE] __attribute__((aligned(64)));
static elem_t tile_b[TILE * TILE] __attribute__((aligned(64)));
static elem_t tile_zero[TILE * TILE] __attribute__((aligned(64)));
static result_t tile_c[TILE * TILE] __attribute__((aligned(64)));
static elem_t matrix_a[MAX_DIM * MAX_DIM], matrix_b[MAX_DIM * MAX_DIM];
static result_t expected[MAX_DIM * MAX_DIM], observed[MAX_DIM * MAX_DIM];

static uint64_t nanoseconds(void) {
  struct timespec value;
  if (clock_gettime(CLOCK_MONOTONIC, &value)) {
    perror("clock_gettime");
    exit(2);
  }
  return (uint64_t)value.tv_sec * 1000000000ULL + value.tv_nsec;
}

static void gemmini_tile(unsigned ws) {
  // 8-byte bank rows: INT8 uses one group, INT32 output uses four groups.
  bb_mem_alloc(0, 1, 1);
  bb_mem_alloc(1, 1, 1);
  bb_mem_alloc(2, 1, 4);
  bb_mem_alloc(3, 1, 1);
  bb_mvin((uintptr_t)tile_a, 0, TILE, 1);
  bb_mvin((uintptr_t)tile_b, 1, TILE, 1);
  bb_mvin((uintptr_t)tile_zero, 3, TILE, 1);
  bb_gemmini_config(ws, 0, 0, 0, 0);
  bb_gemmini_preload(ws ? 1 : 3, 2, TILE, 0, 0);
  bb_gemmini_compute_preloaded(0, ws ? 3 : 1, 2, TILE, 0, 0, 0);
  bb_mvout((uintptr_t)tile_c, 2, TILE, 1);
  bb_fence();
  for (unsigned bank = 0; bank < 4; ++bank)
    bb_mem_release(bank);
}

static void cpu_reference(unsigned m, unsigned n, unsigned k) {
  for (unsigned row = 0; row < m; ++row)
    for (unsigned col = 0; col < n; ++col) {
      int32_t sum = 0;
      for (unsigned inner = 0; inner < k; ++inner)
        sum += (int32_t)matrix_a[row * k + inner] * matrix_b[inner * n + col];
      expected[row * n + col] = sum;
    }
}

static void blocked_matmul(unsigned m, unsigned n, unsigned k, unsigned ws) {
  memset(observed, 0, sizeof(observed));
  for (unsigned row = 0; row < m; row += TILE)
    for (unsigned col = 0; col < n; col += TILE)
      for (unsigned inner = 0; inner < k; inner += TILE) {
        memset(tile_a, 0, sizeof(tile_a));
        memset(tile_b, 0, sizeof(tile_b));
        memset(tile_zero, 0, sizeof(tile_zero));
        // Explicit writes give the DMA destination a private writable page.
        memset(tile_c, 0, sizeof(tile_c));
        for (unsigned i = 0; i < TILE; ++i)
          for (unsigned j = 0; j < TILE; ++j) {
            if (row + i < m && inner + j < k)
              tile_a[i * TILE + j] = matrix_a[(row + i) * k + inner + j];
            if (inner + i < k && col + j < n)
              tile_b[i * TILE + j] = matrix_b[(inner + i) * n + col + j];
          }
        gemmini_tile(ws);
        for (unsigned i = 0; i < TILE && row + i < m; ++i)
          for (unsigned j = 0; j < TILE && col + j < n; ++j)
            observed[(row + i) * n + col + j] += tile_c[i * TILE + j];
      }
}

static int check_case(unsigned id, unsigned m, unsigned n, unsigned k, unsigned ws) {
  // Small bounded values keep the independent INT32 oracle free of overflow.
  for (unsigned i = 0; i < m * k; ++i)
    matrix_a[i] = (int)((i * 7 + id * 3) % 19) - 9;
  for (unsigned i = 0; i < k * n; ++i)
    matrix_b[i] = (int)((i * 11 + id * 5) % 23) - 11;
  printf("BEGIN GEMMINI_CASE id=%u mode=%s m=%u n=%u k=%u\n",
         id, ws ? "WS" : "OS", m, n, k);
  alarm(60);
  uint64_t start = nanoseconds();
  cpu_reference(m, n, k);
  uint64_t cpu_ns = nanoseconds() - start;
  start = nanoseconds();
  blocked_matmul(m, n, k, ws);
  uint64_t accelerator_ns = nanoseconds() - start;
  alarm(0);
  for (unsigned i = 0; i < m * n; ++i)
    if (observed[i] != expected[i]) {
      printf("FAIL GEMMINI_CASE id=%u row=%u col=%u got=%d expected=%d\n",
             id, i / n, i % n, observed[i], expected[i]);
      return 1;
    }
  printf("PASS GEMMINI_CASE id=%u mode=%s m=%u n=%u k=%u cpu_ns=%llu "
         "accelerator_end_to_end_ns=%llu\n", id, ws ? "WS" : "OS", m, n, k,
         (unsigned long long)cpu_ns, (unsigned long long)accelerator_ns);
  return 0;
}

int main(void) {
  setvbuf(stdout, NULL, _IONBF, 0);
  printf("BEGIN GEMMINI_LINUX_CHECK pid=%ld dimension=%d bank_width=%d\n",
         (long)getpid(), GEMMINI_DIM, BANK_WIDTH);
  if (mlockall(MCL_CURRENT | MCL_FUTURE))
    printf("INFO MLOCKALL errno=%d; buffers are explicitly faulted in\n", errno);
  unsigned id = 0;
  const unsigned shapes[][3] = {{8, 8, 8}, {16, 16, 16}, {13, 11, 17}, {8, 24, 8}};
  for (unsigned repeat = 0; repeat < 2; ++repeat)
    for (unsigned shape = 0; shape < sizeof(shapes) / sizeof(shapes[0]); ++shape)
      for (unsigned ws = 0; ws < 2; ++ws)
        if (check_case(++id, shapes[shape][0], shapes[shape][1], shapes[shape][2], ws))
          return 1;
  printf("PASS GEMMINI_LINUX_CHECK cases=%u\n", id);
  return 0;
}
