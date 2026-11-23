"""Check a prepared Windows game folder against single-layer DVD-R capacity."""
from __future__ import annotations
import argparse
from pathlib import Path

DVD_SAFE_LIMIT = 4_300_000_000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    root = args.folder.resolve()
    if not root.is_dir():
        parser.error(f"folder does not exist: {root}")
    files = [path for path in root.rglob("*") if path.is_file()]
    total = sum(path.stat().st_size for path in files)
    gib = total / (1024 ** 3)
    print(f"Files: {len(files)}")
    print(f"Payload: {total:,} bytes ({gib:.3f} GiB)")
    print(f"Single-layer DVD-R safe limit: {DVD_SAFE_LIMIT:,} bytes")
    if total > DVD_SAFE_LIMIT:
        print("ERROR: payload is too large for the selected DVD-R target.")
        return 2
    print("OK: payload fits the DVD-R target with reserve space.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
