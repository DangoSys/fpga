// Four 8x8 column tiles: 11 loop rows exceed the 8-row SubROB.
// Forty alternating OS/WS loops cross the 255-token mesh-tag wrap point.
// Compare every INT32 result against the pinned CPU matrix reference.
#include "buckyball.h"
#include <bbhw/isa/isa.h>
#include <bbhw/mem/mem.h>
#include <isa/gemmini.h>

#define M 8
#define N 32
#define K 8
static elem_t a[M * K] __attribute__((aligned(64)));
static elem_t b[K * N] __attribute__((aligned(64)));
static result_t c[M * N] __attribute__((aligned(64)));
static result_t expected[M * N] __attribute__((aligned(64)));

int main(void) {
  for (int r = 0; r < M; ++r)
    for (int k = 0; k < K; ++k) a[r * K + k] = (r * 3 + k * 5) % 9 - 4;
  for (int k = 0; k < K; ++k)
    for (int n = 0; n < N; ++n) b[k * N + n] = (k * 7 + n * 2) % 11 - 5;
  cpu_matmul(a, b, expected, M, N, K);
  for (int run = 0; run < 40; ++run) {
    int mode = run & 1;
    clear_u32_matrix(c, M, N);
    bb_gemmini_config(mode, 0, 0, 0, 0);
    bb_gemmini_loop_ws_config_bounds(1, 4, 1);
    bb_gemmini_loop_ws_config_addr_a((uintptr_t)a);
    bb_gemmini_loop_ws_config_addr_b((uintptr_t)b);
    bb_gemmini_loop_ws_config_addr_d(0);
    bb_gemmini_loop_ws_config_addr_c((uintptr_t)c);
    bb_gemmini_loop_ws_config_strides_ab(K, N);
    bb_gemmini_loop_ws_config_strides_dc(0, N * 4);
    bb_gemmini_loop_ws(0, 1, 2, 1);
    bb_fence();
    if (!compare_u32_matrices(c, expected, M, N)) return run + 1;
  }
  return 0;
}
