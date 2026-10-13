"""烧录前离线核验下载包中的全部文件；本入口不连接硬件。"""

import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def verify(root):
    root = root.resolve()
    record = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
    for name, expected in record["files"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("下载包文件缺失或路径无效：" + name)
        if path.stat().st_size != expected["bytes"] or digest(path) != expected["sha256"]:
            raise ValueError("下载包摘要不匹配：" + name)
    print(f"PASS BUNDLE {record['flow']} files={len(record['files'])}")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path,
                        default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    verify(args.directory)


if __name__ == "__main__":
    main()
