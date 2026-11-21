"""Extraction of constructive comments and recurring questions."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any


QUESTION_MARK = re.compile(r"[?!]")
WORD_MARK = re.compile(r"[^\w]+", re.UNICODE)


class ThreadExtractor:
    """Filter useful comments and derive a small set of recurring FAQs."""

    def __init__(
        self,
        minimum_score: int = 10,
        minimum_faq_count: int = 2,
        opt_out_commands: Iterable[str] | None = None,
    ) -> None:
        self.minimum_score = minimum_score
        self.minimum_faq_count = minimum_faq_count
        self.opt_out_commands = tuple(
            opt_out_commands or ("!optout",)
        )

    def contains_opt_out(self, text: str) -> bool:
        """Return whether text requests opt-out from digest processing."""
        lowered = text.lower()
        return any(command.lower() in lowered for command in self.opt_out_commands)

    def extract_comments(
        self,
        comments: Iterable[Any],
    ) -> list[dict[str, Any]]:
        """Convert PRAW comments or mappings to safe, non-PII records."""
        extracted: list[dict[str, Any]] = []
        for comment in comments:
            score = self._field(comment, "score", 0)
            body = str(self._field(comment, "body", "")).strip()
            if not body or self.contains_opt_out(body):
                continue
            if int(score) < self.minimum_score:
                continue
            if getattr(comment, "stickied", False):
                continue
            permalink = self._field(comment, "permalink", "")
            extracted.append(
                {
                    "score": int(score),
                    "body": body,
                    "permalink": str(permalink),
                }
            )
        extracted.sort(key=lambda item: item["score"], reverse=True)
        return extracted

    def extract_faqs(
        self,
        threads: Iterable[Any],
    ) -> list[dict[str, Any]]:
        """Find repeated question text across thread titles and comments."""
        normalized_to_text: dict[str, str] = {}
        counts: Counter[str] = Counter()

        for thread in threads:
            title = str(self._field(thread, "title", "")).strip()
            if title and "?" in title:
                normalized = self._normalize(title)
                if normalized:
                    normalized_to_text.setdefault(normalized, title)
                    counts[normalized] += 1

            comments = self._field(thread, "comments", ())
            if hasattr(comments, "list"):
                comments = comments.list()
            for comment in comments:
                body = str(self._field(comment, "body", "")).strip()
                if not body or self.contains_opt_out(body):
                    continue
                first_sentence = re.split(r"[.!?]\s", body, maxsplit=1)[0]
                if QUESTION_MARK.search(first_sentence):
                    normalized = self._normalize(first_sentence)
                    if normalized:
                        normalized_to_text.setdefault(normalized, first_sentence)
                        counts[normalized] += 1

        faqs = [
            {
                "question": normalized_to_text[key],
                "count": count,
            }
            for key, count in counts.items()
            if count >= self.minimum_faq_count
        ]
        return sorted(faqs, key=lambda faq: (-faq["count"], faq["question"]))

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(WORD_MARK.sub(" ", text.lower()).split())

    @staticmethod
    def _field(value: Any, name: str, default: Any) -> Any:
        if isinstance(value, Mapping):
            return value.get(name, default)
        return getattr(value, name, default)
