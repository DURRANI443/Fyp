"""Capture a new documentation baseline; never replace an existing manifest."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re

from check_docs import ROOT, inventory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--date", required=True, type=date.fromisoformat, help="Client-local date, YYYY-MM-DD")
    args = parser.parse_args()
    directory = args.directory.resolve()
    if directory.parent != ROOT / "doc" or not re.fullmatch(r"v\d+\.\d+\.\d+", directory.name):
        parser.error("Choose an existing doc/vMAJOR.MINOR.PATCH directory in this repository.")
    if not directory.is_dir() or not (directory / "README.md").is_file():
        parser.error("Baseline directory and README.md must exist.")
    if any(path.is_symlink() for path in directory.rglob("*")):
        parser.error("Baseline must contain regular files, not symlinks.")
    manifest = directory / "manifest.json"
    if manifest.exists():
        parser.error("This version is already captured. Create a new version instead.")
    files = inventory(directory)
    payload = {
        "schema_version": 1,
        "version": directory.name,
        "captured_on": args.date.isoformat(),
        "timezone": "Asia/Karachi",
        "algorithm": "sha256",
        "scope": "documentation baseline; not an application release or supervisor approval",
        "files": files,
    }
    with manifest.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2) + "\n")
    print(f"Captured {directory.name}: {len(files)} files. Existing baseline files are now immutable.")


if __name__ == "__main__":
    main()
