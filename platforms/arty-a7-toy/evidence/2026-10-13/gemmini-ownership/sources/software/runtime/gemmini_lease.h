#ifndef BB_GEMMINI_LEASE_H
#define BB_GEMMINI_LEASE_H

#include <sys/types.h>

/* One cooperative device, shared by every wrapped Linux workload. Never unlink
 * this file to recover: a platform reset must also stop outstanding DMA. */
#ifndef BB_GEMMINI_LOCK_PATH
#define BB_GEMMINI_LOCK_PATH "/tmp/buckyball-gemmini.lock"
#endif
#define BB_GEMMINI_WAIT_MS 90000U
#define BB_GEMMINI_LEASE_INIT { -1, 0 }
#define BB_GEMMINI_EXIT_BUSY 75
#define BB_GEMMINI_EXIT_DIRTY 76
#define BB_GEMMINI_EXIT_ERROR 74

struct bb_gemmini_lease {
  int fd;
  pid_t owner;
};

/* Returns 0, or -1 with errno (ETIMEDOUT / EUCLEAN / filesystem error).
 * Alternate paths are for isolated host tests only; production uses the path
 * above. A successful acquisition durably marks the device DIRTY. */
int bb_gemmini_lease_acquire(struct bb_gemmini_lease *lease, const char *path,
                             unsigned wait_ms);
/* Call only AFTER the workload succeeded and a hardware completion fence has
 * drained compute, DMA and bank release. A fork child cannot complete it. */
int bb_gemmini_lease_complete(struct bb_gemmini_lease *lease);
/* Close without clearing DIRTY on any failure. Safe in a fork child, too. */
void bb_gemmini_lease_abandon(struct bb_gemmini_lease *lease);

#endif
