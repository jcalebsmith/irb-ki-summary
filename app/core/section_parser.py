"""Helpers for parsing structured section content."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class KISection:
    """Structured representation of a Key Information section."""

    index: int
    title: str
    body: str


_KI_SECTION_PATTERN = re.compile(r"^[ \t]*Section\s+(\d+)\b.*$", re.IGNORECASE | re.MULTILINE)


def parse_ki_sections(content: str) -> List[KISection]:
    """
    Split rendered KI summaries into per-section chunks.

    The renderer emits one `Section <n>` heading per line; whitespace around the
    heading is ignored. This parser treats those headings as anchors so we can
    reconstruct ordered (title, body) pairs regardless of blank-line placement.
    """
    if not content:
        return []

    matches = list(_KI_SECTION_PATTERN.finditer(content))
    sections: List[KISection] = []

    if not matches:
        return sections

    for idx, match in enumerate(matches):
        number = int(match.group(1))
        title = f"Section {number}"
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        body = content[start:end].lstrip("\r\n").rstrip()
        sections.append(KISection(index=number, title=title, body=body))

    return sections
