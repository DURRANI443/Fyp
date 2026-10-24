"""Check local documentation links and immutable baseline inventories."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def inventory(directory: Path) -> dict[str, str]:
    return {
        path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path != directory / "manifest.json"
    }


def main() -> int:
    errors: list[str] = []
    markdown = sorted(ROOT.glob("*.md")) + sorted((ROOT / "doc").rglob("*.md"))
    checked_links = 0
    for path in markdown:
        content = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            target = target.strip().strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            checked_links += 1
            destination = (path.parent / unquote(parsed.path)).resolve()
            if not destination.is_relative_to(ROOT):
                errors.append(f"{path.relative_to(ROOT)}: link leaves repository: {target}")
            elif not destination.exists():
                errors.append(f"{path.relative_to(ROOT)}: missing link: {target}")

    manifests = sorted((ROOT / "doc").glob("v*/manifest.json"))
    for path in manifests:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            expected = data["files"]
            actual = inventory(path.parent)
            for name in sorted(expected.keys() - actual.keys()):
                errors.append(f"{path.parent.name}: missing baseline file: {name}")
            for name in sorted(actual.keys() - expected.keys()):
                errors.append(f"{path.parent.name}: added after capture: {name}")
            for name in sorted(expected.keys() & actual.keys()):
                if expected[name] != actual[name]:
                    errors.append(f"{path.parent.name}: changed after capture: {name}")
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            errors.append(f"Invalid manifest {path.relative_to(ROOT)}: {exc}")

    if errors:
        print("Documentation checks FAILED:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(
        f"PASS: {len(markdown)} Markdown files, {checked_links} local links, "
        f"{len(manifests)} captured baseline(s)."
    )
    print("External links, Markdown anchors, and Mermaid rendering are separate checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
