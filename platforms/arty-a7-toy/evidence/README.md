# Preserved measurements

`2026-10-11/` contains original measured reports and test transcripts from the
selected isolated candidate. The archived report mentions that candidate's
original build paths; repository build/operation instructions are in `../README.md`.
Checkpoints, generated RTL, images and bitstreams are omitted from Git.

The core/RAM hashes and original firmware payload hash identify the exact
measured hardware/software. The archived machine record's source paths and
commands describe the original experiment, not installation requirements.
Portable launchers in `scripts/` use PATH or explicit overrides.

Run `python3 scripts/verify_target.py` from the platform directory to verify
published source hashes, reference oracles, vendor inputs and recorded results.
After elaboration, add `--core` to verify the generated core and RAM binding.
