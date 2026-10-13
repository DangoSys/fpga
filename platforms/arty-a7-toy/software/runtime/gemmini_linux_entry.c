#include "gemmini_lease.h"

#include <errno.h>
#include <stdio.h>
#include <string.h>

int bb_workload_main(void);
void bb_gemmini_drain(void);

/* Workload main is renamed at compilation, leaving pinned reference sources
 * intact. The lease covers setup, every custom instruction and final cleanup. */
int main(void) {
  struct bb_gemmini_lease lease = BB_GEMMINI_LEASE_INIT;
  if (bb_gemmini_lease_acquire(&lease, BB_GEMMINI_LOCK_PATH,
                               BB_GEMMINI_WAIT_MS) < 0) {
    int error = errno;
    fprintf(stderr, "GEMMINI_LEASE rejected errno=%d (%s)\n", error,
            strerror(error));
    if (error == EUCLEAN)
      fprintf(stderr, "GEMMINI_LEASE device state unknown; reset the complete "
                      "FPGA/Linux platform before reuse; do not delete the lock\n");
    return error == ETIMEDOUT ? BB_GEMMINI_EXIT_BUSY :
           error == EUCLEAN ? BB_GEMMINI_EXIT_DIRTY : BB_GEMMINI_EXIT_ERROR;
  }
  fprintf(stderr, "GEMMINI_LEASE acquired pid=%ld\n", (long)lease.owner);
  bb_gemmini_drain();
  int result = bb_workload_main();
  if (result == 0) {
    /* Includes memory releases queued after the workload's own DMA fence. */
    bb_gemmini_drain();
    if (bb_gemmini_lease_complete(&lease) < 0) {
      fprintf(stderr, "GEMMINI_LEASE completion record failed: %s\n",
              strerror(errno));
      bb_gemmini_lease_abandon(&lease);
      return BB_GEMMINI_EXIT_ERROR;
    }
    fprintf(stderr, "GEMMINI_LEASE complete\n");
  } else {
    bb_gemmini_lease_abandon(&lease);
    fprintf(stderr, "GEMMINI_LEASE workload failed; device left DIRTY\n");
  }
  return result;
}
