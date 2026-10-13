#define _GNU_SOURCE
#include "gemmini_lease.h"

#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

static const char clean[] = "BBGM1 CLEAN\n";

static int64_t now_ms(void) {
  struct timespec ts;
  if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0)
    return -1;
  return (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

static int record(int fd, const char *text) {
  size_t length = strlen(text), done = 0;
  while (done < length) {
    ssize_t n = pwrite(fd, text + done, length - done, (off_t)done);
    if (n < 0 && errno == EINTR)
      continue;
    if (n <= 0) {
      if (n == 0)
        errno = EIO;
      return -1;
    }
    done += (size_t)n;
  }
  if (ftruncate(fd, (off_t)length) < 0 || fdatasync(fd) < 0)
    return -1;
  return 0;
}

int bb_gemmini_lease_acquire(struct bb_gemmini_lease *lease, const char *path,
                             unsigned wait_ms) {
  struct stat st;
  char state[96], dirty[96];
  int fd, error;
  int64_t started, deadline;
  if (!lease || !path || lease->fd != -1) {
    errno = EINVAL;
    return -1;
  }
  started = now_ms();
  if (started < 0)
    return -1;
  deadline = started + wait_ms;
  fd = open(path, O_RDWR | O_CREAT | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK, 0600);
  if (fd < 0)
    return -1;
  if (fstat(fd, &st) < 0)
    goto fail;
  if (!S_ISREG(st.st_mode) || st.st_nlink != 1 || st.st_uid != geteuid()) {
    errno = EACCES;
    goto fail;
  }
  for (;;) {
    if (flock(fd, LOCK_EX | LOCK_NB) == 0)
      break;
    if (errno != EWOULDBLOCK && errno != EAGAIN && errno != EINTR)
      goto fail;
    int64_t now = now_ms();
    if (now < 0)
      goto fail;
    if (now >= deadline) {
      errno = ETIMEDOUT;
      goto fail;
    }
    int64_t delay = deadline - now;
    if (delay > 10)
      delay = 10;
    struct timespec pause = {0, delay * 1000000};
    /* A signal does not extend the monotonic deadline. */
    if (nanosleep(&pause, NULL) < 0 && errno != EINTR)
      goto fail;
  }
  if (fstat(fd, &st) < 0)
    goto fail;
  if (st.st_nlink != 1 || st.st_size > (off_t)sizeof(state)) {
    errno = EUCLEAN;
    goto fail;
  }
  ssize_t length;
  do {
    length = pread(fd, state, sizeof(state), 0);
  } while (length < 0 && errno == EINTR);
  if (length < 0)
    goto fail;
  /* An empty new record is safe: no owner has been allowed to issue hardware
   * instructions yet. Any partial, stale or unknown record fails closed. */
  if (length != 0 &&
      (length != (ssize_t)(sizeof(clean) - 1) ||
       memcmp(state, clean, sizeof(clean) - 1) != 0)) {
    errno = EUCLEAN;
    goto fail;
  }
  snprintf(dirty, sizeof(dirty), "BBGM1 DIRTY pid=%ld\n", (long)getpid());
  if (record(fd, dirty) < 0)
    goto fail;
  lease->fd = fd;
  lease->owner = getpid();
  return 0;
fail:
  error = errno;
  close(fd);
  errno = error;
  return -1;
}

int bb_gemmini_lease_complete(struct bb_gemmini_lease *lease) {
  if (!lease || lease->fd < 0) {
    errno = EINVAL;
    return -1;
  }
  if (lease->owner != getpid()) {
    errno = EPERM;
    return -1;
  }
  if (record(lease->fd, clean) < 0)
    return -1;
  /* No explicit LOCK_UN: fork children may share this open file description.
   * Closing the last descriptor releases it; O_CLOEXEC prevents exec leaks. */
  bb_gemmini_lease_abandon(lease);
  return 0;
}

void bb_gemmini_lease_abandon(struct bb_gemmini_lease *lease) {
  if (lease && lease->fd >= 0) {
    close(lease->fd);
    lease->fd = -1;
    lease->owner = 0;
  }
}
