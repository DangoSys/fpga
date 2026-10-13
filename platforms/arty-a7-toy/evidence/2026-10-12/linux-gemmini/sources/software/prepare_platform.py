"""Prepare the original bbkernel with board memory/timebase adaptations only.

This prepares sources, not a kernel image. It never modifies a shared checkout.
"""

import hashlib
import io
import json
import tarfile
import urllib.request
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads((ROOT / "SOFTWARE_BASELINE.json").read_text())
OUTPUT = ROOT / "build/software/bb-tests/workloads/lib/kernel"


def prepare():
    commit = BASELINE["bbkernel"]
    url = f"https://codeload.github.com/DangoSys/bbkernel/tar.gz/{commit}"
    cache = ROOT / "build/downloads" / f"bbkernel-{commit}.tar.gz"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if not cache.exists():
        with urllib.request.urlopen(url, timeout=60) as response:
            archive = response.read()
        cache.write_bytes(archive)
    changes = {
        "opensbi-platform/buckyball/platform.c": (
            b"#define BUCKYBALL_MTIMER_FREQ 10000000",
            b"#define BUCKYBALL_MTIMER_FREQ 1000000",
        ),
        "config/linux-config": (b"mem=512M", b"mem=256M"),
    }
    records = {}
    with tarfile.open(fileobj=io.BytesIO(cache.read_bytes())) as source:
        for member in source:
            if not member.isfile():
                continue
            relative = PurePosixPath(*PurePosixPath(member.name).parts[1:])
            if not relative.parts or relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Unsafe archive member: {member.name}")
            data = source.extractfile(member).read()
            original = hashlib.sha256(data).hexdigest()
            name = relative.as_posix()
            if name in changes:
                before, after = changes[name]
                if data.count(before) != 1:
                    raise ValueError(
                        f"Expected exactly one board adaptation site: {name}"
                    )
                data = data.replace(before, after)
            target = OUTPUT / name
            if target.exists() and target.read_bytes() != data:
                raise RuntimeError(
                    f"Refusing to overwrite changed platform source: {target}"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            records[name] = {
                "original_sha256": original,
                "fpga_sha256": hashlib.sha256(data).hexdigest(),
            }
    assert changes.keys() <= records.keys()
    config = (OUTPUT / "config/linux-config").read_text()
    for required in (
        "CONFIG_RISCV_ROCC=y",
        "CONFIG_HVC_RISCV_SBI=y",
        "CONFIG_RISCV_SBI_V01=y",
    ):
        assert required in config, required
    result = {
        "repository": "https://github.com/DangoSys/bbkernel",
        "commit": commit,
        "archive_sha256": hashlib.sha256(cache.read_bytes()).hexdigest(),
        "adaptations": {"clint_hz": 1000000, "memory_limit_mib": 256},
        "files": records,
        "kernel_image_built": False,
    }
    (ROOT / "build/software/SOURCE_MANIFEST.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(
        f"Prepared {len(records)} pinned bbkernel files; "
        "two board adaptations; no image built"
    )


if __name__ == "__main__":
    prepare()
