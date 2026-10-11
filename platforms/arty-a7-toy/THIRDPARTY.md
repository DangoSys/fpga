# Third-party source provenance

`UPSTREAM_MANIFEST.json` pins the exported Buckyball source commit and every
file hash. `dependencies.json` pins CDE, Diplomacy, Rocket Chip, HardFloat,
inclusive cache, Gemmini and FireSim snapshots. `prepare_sources.py` exports
their license/notice files alongside ignored dependency sources. Keep those
notices when redistributing exported or modified dependency code.

Pinned original test/library files are under `tests/reference/`, with hashes in
`tests/REFERENCE_MANIFEST.json`, from the same Buckyball revision. The FPGA
repository's license remains at the repository root.

`board/vendor/MANIFEST.json` records the Digilent vivado-boards commit, original
URLs and SHA256 values for the unmodified Arty A7-100T E.0 board/MIG files.
Vivado generates AMD/Xilinx IP locally; generated vendor RTL is not committed.

`SOFTWARE_BASELINE.json` pins bbkernel, Linux, OpenSBI and BusyBox. Their sources
and original licenses are fetched into ignored `build/software/`; software
adaptations affect board memory/timebase properties, not the Linux ISA model.
