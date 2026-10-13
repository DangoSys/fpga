/* Host mock: emits NO custom instructions. Tests entry ordering and refusal. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

void bb_gemmini_drain(void) { puts("MOCK_DRAIN"); }

int bb_workload_main(void) {
  puts("MOCK_WORKLOAD");
  if (getenv("BB_TEST_SLEEP"))
    sleep(3);
  return getenv("BB_TEST_FAIL") ? 1 : 0;
}
