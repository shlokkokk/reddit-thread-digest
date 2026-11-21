"""Command-line entry point for reddit-thread-digest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console

from src.archiver.bot import RedditBot
from src.archiver.compiler import build_markdown_digest
from src.archiver.config import load_credentials, load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Archive constructive Reddit discussions and generate digests.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--monitor",
        action="store_true",
        help="listen to configured subreddit streams",
    )
    mode.add_argument(
        "--generate-digest",
        action="store_true",
        help="generate Markdown from an exported JSON dataset",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="disable Reddit writes (recommended and default for monitoring)",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="input JSON file containing title, category, score, url, and summary",
    )
    parser.add_argument("--output", type=Path, help="write digest to this file")
    parser.add_argument(
        "--config",
        type=Path,
        help="YAML configuration path",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    console = Console()
    settings = load_settings(args.config)
    credentials = load_credentials()

    if args.generate_digest:
        if not args.input:
            console.print("[bold red]--generate-digest requires --input[/bold red]")
            return 2
        try:
            with args.input.open("r", encoding="utf-8") as handle:
                entries = json.load(handle)
        except (OSError, json.JSONDecodeError) as error:
            console.print(f"[bold red]Unable to read input: {error}[/bold red]")
            return 2
        digest = build_markdown_digest(
            entries,
            title=settings["templates"]["digest_title"],
        )
        if args.output:
            args.output.write_text(digest, encoding="utf-8")
            console.print(f"Digest written to {args.output}")
        else:
            sys.stdout.write(digest)
        return 0

    if not args.dry_run:
        missing = [
            name
            for name, value in (
                ("REDDIT_CLIENT_ID", credentials.client_id),
                ("REDDIT_CLIENT_SECRET", credentials.client_secret),
                ("REDDIT_USERNAME", credentials.username),
                ("REDDIT_PASSWORD", credentials.password),
            )
            if not value
        ]
        if missing:
            console.print(
                "[bold red]Missing environment variables: "
                + ", ".join(missing)
                + "[/bold red]"
            )
            return 2

    try:
        import praw

        reddit_options = {
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "username": credentials.username,
            "password": credentials.password,
            "user_agent": credentials.user_agent,
        }
        if args.dry_run:
            reddit_options = {
                "client_id": credentials.client_id or "dry-run",
                "client_secret": credentials.client_secret or "dry-run",
                "user_agent": credentials.user_agent,
                "read_only": True,
            }
        reddit = praw.Reddit(**reddit_options)
    except Exception as error:
        console.print(f"[bold red]Unable to initialize PRAW: {error}[/bold red]")
        return 2

    bot = RedditBot(
        reddit,
        settings["subreddits"],
        dry_run=args.dry_run,
        requests_per_minute=settings["requests_per_minute"],
        write_cooldown_seconds=settings["write_cooldown_seconds"],
    )
    console.print(
        "[yellow]Dry run[/yellow]: no Reddit writes"
        if args.dry_run
        else "[green]Live monitoring[/green]"
    )
    bot.monitor()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
