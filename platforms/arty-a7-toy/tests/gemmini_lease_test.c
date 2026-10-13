#define _GNU_SOURCE
#include "gemmini_lease.h"

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define CHECK(x) do { if (!(x)) { \
  fprintf(stderr, "FAIL line=%d %s errno=%d\n", __LINE__, #x, errno); exit(1); \
} } while (0)

struct counters { int active, completed, conflicts; };

static void joined(pid_t pid) {
  int status;
  CHECK(waitpid(pid, &status, 0) == pid);
  CHECK(WIFEXITED(status) && WEXITSTATUS(status) == 0);
}

static void token(int fd) {
  char value;
  CHECK(read(fd, &value, 1) == 1);
}

static void notify(int fd) { CHECK(write(fd, "x", 1) == 1); }

static void reuse(const char *path) {
  for (int i = 0; i < 3; ++i) {
    struct bb_gemmini_lease lease = BB_GEMMINI_LEASE_INIT;
    CHECK(bb_gemmini_lease_acquire(&lease, path, 100) == 0);
    CHECK(bb_gemmini_lease_acquire(&lease, path, 0) < 0 && errno == EINVAL);
    CHECK(bb_gemmini_lease_complete(&lease) == 0);
    CHECK(lease.fd == -1);
  }
  puts("PASS lease_clean_reuse");
}

static void contention(const char *path) {
  enum { CHILDREN = 6, ITERATIONS = 20 };
  int gate[2];
  pid_t pids[CHILDREN];
  struct counters *c = mmap(NULL, sizeof(*c), PROT_READ | PROT_WRITE,
                             MAP_SHARED | MAP_ANONYMOUS, -1, 0);
  CHECK(c != MAP_FAILED && pipe(gate) == 0);
  memset(c, 0, sizeof(*c));
  for (int i = 0; i < CHILDREN; ++i) {
    pids[i] = fork();
    CHECK(pids[i] >= 0);
    if (pids[i] == 0) {
      close(gate[1]);
      token(gate[0]);
      close(gate[0]);
      for (int j = 0; j < ITERATIONS; ++j) {
        struct bb_gemmini_lease lease = BB_GEMMINI_LEASE_INIT;
        CHECK(bb_gemmini_lease_acquire(&lease, path, 5000) == 0);
        if (c->active != 0)
          ++c->conflicts;
        ++c->active;
        struct timespec delay = {0, 1000000};
        nanosleep(&delay, NULL);
        CHECK(c->active == 1);
        --c->active;
        ++c->completed;
        CHECK(bb_gemmini_lease_complete(&lease) == 0);
      }
      _exit(0);
    }
  }
  close(gate[0]);
  for (int i = 0; i < CHILDREN; ++i)
    notify(gate[1]);
  close(gate[1]);
  for (int i = 0; i < CHILDREN; ++i)
    joined(pids[i]);
  CHECK(c->active == 0 && c->completed == CHILDREN * ITERATIONS &&
        c->conflicts == 0);
  munmap(c, sizeof(*c));
  puts("PASS lease_concurrency processes=6 transactions=120 overlap=0");
}

static void timeout_and_inherited(const char *path) {
  struct bb_gemmini_lease owner = BB_GEMMINI_LEASE_INIT;
  CHECK(bb_gemmini_lease_acquire(&owner, path, 0) == 0);
  pid_t child = fork();
  CHECK(child >= 0);
  if (child == 0) {
    CHECK(bb_gemmini_lease_complete(&owner) < 0 && errno == EPERM);
    /* Closing a child's inherited copy must not explicitly unlock the parent. */
    bb_gemmini_lease_abandon(&owner);
    struct bb_gemmini_lease waiter = BB_GEMMINI_LEASE_INIT;
    struct timespec before, after;
    CHECK(clock_gettime(CLOCK_MONOTONIC, &before) == 0);
    CHECK(bb_gemmini_lease_acquire(&waiter, path, 40) < 0 &&
          errno == ETIMEDOUT);
    CHECK(clock_gettime(CLOCK_MONOTONIC, &after) == 0);
    double ms = (after.tv_sec - before.tv_sec) * 1000.0 +
                (after.tv_nsec - before.tv_nsec) / 1000000.0;
    CHECK(ms >= 35 && ms < 1000);
    _exit(0);
  }
  joined(child);
  CHECK(bb_gemmini_lease_complete(&owner) == 0);
  puts("PASS lease_timeout_and_fork_owner");
}

static void killed_owner(const char *path) {
  int ready[2], status;
  CHECK(pipe(ready) == 0);
  pid_t child = fork();
  CHECK(child >= 0);
  if (child == 0) {
    struct bb_gemmini_lease lease = BB_GEMMINI_LEASE_INIT;
    close(ready[0]);
    CHECK(bb_gemmini_lease_acquire(&lease, path, 0) == 0);
    notify(ready[1]);
    close(ready[1]);
    for (;;)
      pause();
  }
  close(ready[1]);
  token(ready[0]);
  close(ready[0]);
  CHECK(kill(child, SIGKILL) == 0);
  CHECK(waitpid(child, &status, 0) == child && WIFSIGNALED(status) &&
        WTERMSIG(status) == SIGKILL);
  struct bb_gemmini_lease next = BB_GEMMINI_LEASE_INIT;
  CHECK(bb_gemmini_lease_acquire(&next, path, 100) < 0 && errno == EUCLEAN);
  CHECK(next.fd == -1);
  puts("PASS lease_sigkill_sticky_dirty");
}

static void abandoned_owner(const char *path) {
  struct bb_gemmini_lease lease = BB_GEMMINI_LEASE_INIT;
  CHECK(bb_gemmini_lease_acquire(&lease, path, 0) == 0);
  bb_gemmini_lease_abandon(&lease);
  CHECK(bb_gemmini_lease_acquire(&lease, path, 0) < 0 && errno == EUCLEAN);
  puts("PASS lease_failure_sticky_dirty");
}

static void bad_record(const char *path) {
  int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
  CHECK(fd >= 0 && write(fd, "BBGM1 CLE", 9) == 9 && close(fd) == 0);
  struct bb_gemmini_lease lease = BB_GEMMINI_LEASE_INIT;
  CHECK(bb_gemmini_lease_acquire(&lease, path, 0) < 0 && errno == EUCLEAN);
  puts("PASS lease_partial_record_rejected");
}

int main(int argc, char **argv) {
  char path[1024], target[1024];
  CHECK(argc == 2);
  snprintf(path, sizeof(path), "%s/clean.lock", argv[1]);
  reuse(path);
  contention(path);
  timeout_and_inherited(path);
  snprintf(path, sizeof(path), "%s/killed.lock", argv[1]);
  killed_owner(path);
  snprintf(path, sizeof(path), "%s/failed.lock", argv[1]);
  abandoned_owner(path);
  snprintf(path, sizeof(path), "%s/partial.lock", argv[1]);
  bad_record(path);
  snprintf(target, sizeof(target), "%s/clean.lock", argv[1]);
  snprintf(path, sizeof(path), "%s/symlink.lock", argv[1]);
  CHECK(symlink(target, path) == 0);
  struct bb_gemmini_lease lease = BB_GEMMINI_LEASE_INIT;
  CHECK(bb_gemmini_lease_acquire(&lease, path, 0) < 0 && errno == ELOOP);
  puts("PASS lease_symlink_rejected");
  puts("PASS GEMMINI_LEASE_HOST_TESTS cases=7 hardware_tested=0");
  return 0;
}
