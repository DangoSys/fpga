"""Fetch the three pinned OS dependencies into this platform's build directory."""

import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads((ROOT / "SOFTWARE_BASELINE.json").read_text())
REPOSITORIES = {
    "linux": "firesim/linux",
    "opensbi": "riscv-software-src/opensbi",
    "busybox": "mirror/busybox",
}


def main():
    cache = ROOT / "build/downloads"
    cache.mkdir(parents=True, exist_ok=True)
    destination = ROOT / "build/software/bb-tests/thirdparty"
    destination.mkdir(parents=True, exist_ok=True)
    for name, repository in REPOSITORIES.items():
        commit = BASELINE[name]
        target = destination / name
        marker = destination / f"{name}.commit"
        if target.exists():
            if not marker.exists() or marker.read_text().strip() != commit:
                raise RuntimeError(f"Unrecognized existing source directory: {target}")
            print(f"Reusing {name} at {commit}", flush=True)
            continue
        archive = cache / f"{name}-{commit}.tar.gz"
        if not archive.exists():
            temporary = archive.with_suffix(".partial")
            subprocess.run(
                [
                    "curl",
                    "--fail",
                    "--location",
                    "--retry",
                    "2",
                    "--connect-timeout",
                    "15",
                    "--max-time",
                    "600",
                    f"https://codeload.github.com/{repository}/tar.gz/{commit}",
                    "--output",
                    str(temporary),
                ],
                check=True,
            )
            temporary.replace(archive)
        staging = destination / f".extract-{name}-{commit}"
        staging.mkdir(exist_ok=True)
        with tarfile.open(archive) as source:
            prefixes = {member.name.split("/")[0] for member in source.getmembers()}
            assert len(prefixes) == 1, "Expected one Git archive root"
            prefix = prefixes.pop()
            assert prefix not in ("", ".", "..")
            source.extractall(staging, filter="data")
        (staging / prefix).rename(target)
        staging.rmdir()
        marker.write_text(commit + "\n")
        print(f"Prepared {repository} at {commit}", flush=True)


if __name__ == "__main__":
    main()
