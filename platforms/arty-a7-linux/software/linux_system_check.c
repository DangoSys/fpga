// Linux acceptance workload: processes, Sv39-backed memory and floating point.
// A host run validates the test program only; the FPGA run is the acceptance.
#define _GNU_SOURCE
#include <errno.h>
#include <math.h>
#include <sched.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static void fail(const char *message) {
  fprintf(stderr, "FAIL %s\n", message);
  exit(1);
}

static int wait_child(pid_t pid) {
  int status;
  pid_t result;
  do {
    result = waitpid(pid, &status, 0);
  } while (result < 0 && errno == EINTR);
  if (result != pid)
    fail("waitpid");
  return status;
}

static void check_virtual_memory(void) {
  long page_size = sysconf(_SC_PAGESIZE);
  if (page_size <= 0)
    fail("page size");
  volatile unsigned char *memory = mmap(NULL, (size_t)page_size * 2,
      PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (memory == MAP_FAILED)
    fail("mmap");
  memory[0] = 0x42;
  memory[page_size] = 0x7b;

  pid_t child = fork();
  if (child < 0)
    fail("fork for copy-on-write");
  if (child == 0) {
    if (memory[0] != 0x42)
      _exit(2);
    memory[0] = 0xa5;
    _exit(memory[0] == 0xa5 ? 0 : 3);
  }
  int status = wait_child(child);
  if (!WIFEXITED(status) || WEXITSTATUS(status) != 0 || memory[0] != 0x42)
    fail("process isolation / copy-on-write");
  puts("PASS VM_COPY_ON_WRITE");

  if (mprotect((void *)(memory + page_size), (size_t)page_size, PROT_NONE))
    fail("mprotect");
  child = fork();
  if (child < 0)
    fail("fork for page fault");
  if (child == 0) {
    volatile unsigned char forbidden = memory[page_size];
    (void)forbidden;
    _exit(4);
  }
  status = wait_child(child);
  if (!WIFSIGNALED(status) || WTERMSIG(status) != SIGSEGV)
    fail("protected page must deliver SIGSEGV");
  if (mprotect((void *)(memory + page_size), (size_t)page_size, PROT_READ))
    fail("restore page access");
  if (memory[page_size] != 0x7b)
    fail("page contents after protection change");
  if (munmap((void *)memory, (size_t)page_size * 2))
    fail("munmap");
  puts("PASS VM_PAGE_PROTECTION");
}

static int float_work(double seed) {
  volatile double scale = 1.5;
  double value = seed;
  for (int i = 0; i < 1000; ++i) {
    value = value * scale + 0.25;
    if (sched_yield())
      return 1;
    value = (value - 0.25) / scale;
    if (!isfinite(value) || fabs(value - seed) > 1e-10)
      return 1;
  }
  return 0;
}

static void check_float_context(void) {
  pid_t child = fork();
  if (child < 0)
    fail("fork for floating-point context");
  if (child == 0)
    _exit(float_work(-3.125));
  int parent_result = float_work(7.25);
  int status = wait_child(child);
  if (parent_result || !WIFEXITED(status) || WEXITSTATUS(status))
    fail("floating-point arithmetic/context");
  puts("PASS FP64_PROCESS_CONTEXT");
}

static void check_timer(void) {
  struct timespec before, after, remaining = {0, 100000000};
  if (clock_gettime(CLOCK_MONOTONIC, &before))
    fail("clock_gettime start");
  while (nanosleep(&remaining, &remaining)) {
    if (errno != EINTR)
      fail("nanosleep");
  }
  if (clock_gettime(CLOCK_MONOTONIC, &after))
    fail("clock_gettime end");
  int64_t elapsed = (after.tv_sec - before.tv_sec) * INT64_C(1000000000)
      + after.tv_nsec - before.tv_nsec;
  if (elapsed < 100000000)
    fail("monotonic timer / scheduled wakeup");
  printf("PASS LINUX_TIMER elapsed_ns=%lld\n", (long long)elapsed);
}

int main(void) {
  const struct rlimit no_core_dump = {0, 0};
  if (setrlimit(RLIMIT_CORE, &no_core_dump))
    fail("disable expected-fault core dumps");
  setvbuf(stdout, NULL, _IONBF, 0);
  puts("BEGIN LINUX_SYSTEM_CHECK");
  check_virtual_memory();
  check_float_context();
  check_timer();
  puts("PASS LINUX_SYSTEM_CHECK");
  return 0;
}
