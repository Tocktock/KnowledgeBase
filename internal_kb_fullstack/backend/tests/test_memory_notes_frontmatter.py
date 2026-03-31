from __future__ import annotations

from pathlib import Path
import re


REQUIRED_KEYS = {
    "date",
    "feature",
    "type",
    "related_specs",
    "related_decisions",
    "status",
}
MEMORY_NOTE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-.*\.md$")


def _frontmatter_keys(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return set()

    closing_index = text.find("\n---", 4)
    if closing_index == -1:
        return set()

    frontmatter = text[4:closing_index]
    keys: set[str] = set()
    for line in frontmatter.splitlines():
        if not line or line.startswith(" ") or ":" not in line:
            continue
        key, _separator, _value = line.partition(":")
        keys.add(key.strip())
    return keys


def test_all_memory_notes_include_required_frontmatter() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    memory_root = repo_root / "docs" / "memories"
    missing: list[str] = []

    for path in sorted(memory_root.rglob("*.md")):
        if path.name == "README.md" or not MEMORY_NOTE_RE.match(path.name):
            continue
        missing_keys = REQUIRED_KEYS.difference(_frontmatter_keys(path))
        if missing_keys:
            missing.append(f"{path.relative_to(repo_root)} missing {sorted(missing_keys)}")

    assert not missing, "\n".join(missing)
