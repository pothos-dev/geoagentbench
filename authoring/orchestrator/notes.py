"""Parse `audit/AUTHORING_HISTORY.md` written by a task-design agent.

The agent commits to a fixed nine-section schema. We grep for H2
headers to pull each section's body. Section bodies are returned as
strings; downstream code does any further structuring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Status = Literal["completed", "completed-with-caveats", "unsolvable", "unknown"]
Severity = Literal["low", "med", "high"]

REQUIRED_SECTIONS = (
    "Status",
    "Summary",
    "Verification results",
    "Failure-mode coverage",
    "Open issues",
    "Suggested prompt changes",
    "Inventory change proposals",
    "Library extensions",
    "Runtime",
)


@dataclass
class OpenIssue:
    severity: Severity
    text: str


@dataclass
class Notes:
    task_id: str
    status: Status
    summary: str
    verification: str
    failure_modes: str
    open_issues: list[OpenIssue]
    suggested_prompt_changes: str
    inventory_change_proposals: str
    library_extensions: str
    runtime_minutes: float | None
    raw: str

    @property
    def has_high_severity(self) -> bool:
        return any(i.severity == "high" for i in self.open_issues)


def parse_notes(notes_path: Path, task_id: str) -> Notes:
    text = notes_path.read_text(encoding="utf-8") if notes_path.exists() else ""
    sections = _split_sections(text)
    status_raw = sections.get("Status", "").strip().lower()
    status: Status = (
        "completed"
        if "completed" == status_raw
        else "completed-with-caveats"
        if "with-caveats" in status_raw
        else "unsolvable"
        if "unsolvable" in status_raw
        else "unknown"
    )
    return Notes(
        task_id=task_id,
        status=status,
        summary=sections.get("Summary", "").strip(),
        verification=sections.get("Verification results", "").strip(),
        failure_modes=sections.get("Failure-mode coverage", "").strip(),
        open_issues=_parse_open_issues(sections.get("Open issues", "")),
        suggested_prompt_changes=sections.get("Suggested prompt changes", "").strip(),
        inventory_change_proposals=sections.get(
            "Inventory change proposals", ""
        ).strip(),
        library_extensions=sections.get("Library extensions", "").strip(),
        runtime_minutes=_parse_runtime(sections.get("Runtime", "")),
        raw=text,
    )


def _split_sections(text: str) -> dict[str, str]:
    pattern = re.compile(r"^## (?P<header>.+?)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        header = m.group("header").strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out[header] = text[start:end]
    return out


def _parse_open_issues(body: str) -> list[OpenIssue]:
    issues: list[OpenIssue] = []
    pattern = re.compile(
        r"^- \[severity:\s*(?P<sev>low|med|high)\]\s*[—-]\s*(?P<text>.+)$",
        re.MULTILINE | re.IGNORECASE,
    )
    for m in pattern.finditer(body):
        sev = m.group("sev").lower()
        if sev not in {"low", "med", "high"}:
            continue
        issues.append(OpenIssue(severity=sev, text=m.group("text").strip()))  # type: ignore[arg-type]
    return issues


def _parse_runtime(body: str) -> float | None:
    m = re.search(r"(?P<n>\d+(\.\d+)?)\s*min", body)
    if m:
        return float(m.group("n"))
    return None
