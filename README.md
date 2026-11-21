# reddit-thread-digest

`reddit-thread-digest` is a small, open-source community discussion archiver
built with PRAW. It watches a focused set of lifestyle, curiosity, and advice
subreddits, extracts constructive high-voted comments, identifies recurring
questions, and produces structured weekly Markdown digests.

## Architecture

- `main.py` provides the command-line interface.
- `src/archiver/config.py` loads YAML settings and Reddit OAuth credentials.
- `src/archiver/extractor.py` filters comments and finds recurring FAQs.
- `src/archiver/compiler.py` renders digest and contextual archive Markdown.
- `src/archiver/bot.py` contains the PRAW stream listener and write guard.

Processing is intentionally in-memory. The application does not maintain a
user database or persist usernames, profile data, or other user PII. Cached
thread and comment IDs exist only for duplicate suppression during a process
lifetime.

## Responsible Builder Policy

This project is designed to cooperate with Reddit rate limits and community
moderation controls:

- Live read traffic is capped below 10 requests per minute.
- Submissions and replies require at least 120 seconds between write actions.
- The default is a dry run, and `--monitor` must be explicitly live.
- Processing uses temporary in-memory data only; no user PII is stored.
- A comment or post containing `!optout` is excluded from digests and replies.
- Archive output identifies source URLs rather than reproducing personal
  profile information.

Operators remain responsible for the subreddit's rules, API authorization,
and local scheduling policy.

## Installation

Python 3.10 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config/settings.example.yaml config/settings.yaml
```

Create a Reddit application and export OAuth credentials:

```bash
export REDDIT_CLIENT_ID="..."
export REDDIT_CLIENT_SECRET="..."
export REDDIT_USERNAME="..."
export REDDIT_PASSWORD="..."
export REDDIT_USER_AGENT="reddit-thread-digest/1.0"
```

Environment variables can be placed in `.env`. YAML settings control
subreddits, cooldowns, category tags, templates, opt-out commands, and
exclusion filters.

## CLI usage

Inspect a monitor cycle without writing to Reddit:

```bash
python main.py --dry-run --monitor
```

Monitor configured subreddits and enable permitted writes:

```bash
python main.py --monitor
```

Generate a Markdown digest from an exported local thread dataset:

```bash
python main.py --generate-digest --input weekly_threads.json
```

The digest command writes Markdown to standard output unless `--output` is
provided.