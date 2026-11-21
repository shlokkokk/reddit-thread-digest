"""Markdown formatting for digests and contextual archive replies."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any


def detect_opt_out(text: str, commands: Iterable[str] | None = None) -> bool:
    """Return True when text contains an opt-out command."""
    lowered = (text or "").lower()
    return any(command.lower() in lowered for command in (commands or ("!optout",)))


def escape_markdown(text: str) -> str:
    """Escape Markdown control characters in untrusted text."""
    return re.sub(r"([\\`*_{}\[\]()#+<>|])", r"\\\1", str(text))


def build_contextual_reply(
    thread_title: str,
    archive_url: str,
    opt_out_commands: Iterable[str] | None = None,
) -> str:
    """Build a short contextual reply linking back to an archive."""
    if detect_opt_out(thread_title, opt_out_commands):
        return ""
    title = escape_markdown(thread_title)
    return f"Archived context: [{title}]({archive_url})"


def build_markdown_digest(
    entries: Iterable[Mapping[str, Any]],
    title: str = "Weekly Community Digest",
) -> str:
    """Build a structured Markdown digest from extracted thread records."""
    lines = [f"# {title}", ""]
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for entry in entries:
        if detect_opt_out(str(entry.get("title", ""))):
            continue
        category = str(entry.get("category", "Discussion"))
        grouped.setdefault(category, []).append(entry)

    if not grouped:
        lines.extend(["No qualifying discussions for this period.", ""])
        return "\n".join(lines).rstrip() + "\n"

    for category in sorted(grouped):
        lines.extend([f"## {escape_markdown(category)}", ""])
        for entry in sorted(
            grouped[category],
            key=lambda item: int(item.get("score", 0)),
            reverse=True,
        ):
            thread_title = escape_markdown(str(entry.get("title", "Untitled")))
            url = str(entry.get("url", "")).strip()
            score = int(entry.get("score", 0))
            heading = f"[{thread_title}]({url})" if url else thread_title
            lines.append(f"- {heading} — {score} points")
            summary = str(entry.get("summary", "")).strip()
            if summary:
                lines.append(f"  - {escape_markdown(summary)}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


class MarkdownCompiler:
    """Compatibility wrapper for Markdown formatting helpers."""

    def __init__(self, title: str = "Weekly Community Digest") -> None:
        self.title = title

    def build_digest(self, entries: Iterable[Mapping[str, Any]]) -> str:
        return build_markdown_digest(entries, self.title)

    def build_contextual_reply(
        self,
        thread_title: str,
        archive_url: str,
        opt_out_commands: Iterable[str] | None = None,
    ) -> str:
        return build_contextual_reply(
            thread_title,
            archive_url,
            opt_out_commands,
        )


# Concise public names retained for external callers.
build_digest = build_markdown_digest
build_archive_reply = build_contextual_reply
