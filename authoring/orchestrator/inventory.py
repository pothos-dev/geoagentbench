r"""Parse `authoring/inventory.md` to extract per-task records.

The inventory is structured as ``### Task: `<slug>` `` blocks with a
fixed-shape markdown table of fields plus an output-artifacts list and
a story paragraph. We extract enough to (a) order tasks by difficulty,
(b) hand the inventory block verbatim to the task-design agent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


DIFFICULTY_ORDER = {"L1": 0, "L2": 1, "L3": 2}


@dataclass
class TaskRecord:
    slug: str
    category: str
    difficulty: str  # "L1" | "L2" | "L3"
    region: str
    block: str  # the verbatim markdown block for this task

    @property
    def sort_key(self) -> tuple[int, str]:
        return (DIFFICULTY_ORDER[self.difficulty], self.slug)


def parse_inventory(inventory_path: Path) -> list[TaskRecord]:
    text = inventory_path.read_text(encoding="utf-8")
    # Split on the H3 task-block markers. Each task block ends at the
    # next H3 / H2 header or end of file.
    pattern = re.compile(r"^### Task: `(?P<slug>[^`]+)`\s*$", re.MULTILINE)
    matches = list(pattern.finditer(text))

    records: list[TaskRecord] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else _next_h2_or_eof(
            text, start
        )
        block = text[start:end].strip()
        slug = m.group("slug")
        record = TaskRecord(
            slug=slug,
            category=_extract_field(block, "Category"),
            difficulty=_extract_field(block, "Difficulty"),
            region=_extract_field(block, "Region"),
            block=block,
        )
        records.append(record)

    return records


def order_tasks(records: list[TaskRecord]) -> list[TaskRecord]:
    return sorted(records, key=lambda r: r.sort_key)


def _next_h2_or_eof(text: str, start: int) -> int:
    h2 = re.search(r"^## ", text[start:], re.MULTILINE)
    return start + h2.start() if h2 else len(text)


def _extract_field(block: str, field: str) -> str:
    pattern = rf"^\| {re.escape(field)} \| (?P<value>.*?) \|\s*$"
    m = re.search(pattern, block, re.MULTILINE)
    if not m:
        return ""
    return m.group("value").strip()
