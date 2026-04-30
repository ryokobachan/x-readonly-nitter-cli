---
name: x-readonly-nitter-cli
description: Fetch tweets from Twitter/X without API keys using Nitter. Use when the user wants to retrieve tweets, search Twitter posts, collect tweets from a specific user, search by keywords, or analyze tweet data. Works for fetching recent tweets, historical tweets with date filters, or unlimited cursor-based pagination.
version: 1.0.0
allowed-tools: Bash(eneet *)
---

# X Read-Only Nitter CLI — Tweet Fetcher via Nitter

`eneet` is a CLI tool for fetching tweets via Nitter (a privacy-respecting Twitter frontend). No API keys required. The repository is named `x-readonly-nitter-cli`; the installed command remains `eneet`.

## Installation

```bash
pip install eneet
# or from source
pip install -e /path/to/eneet
```

## Core Behavior

- **Default (no `-o`)**: streams each tweet as a JSON line to stdout
- **With `-o`**: saves to JSONL file (one tweet per line)
- **Errors only** go to stderr — stdout is pure JSON data

## Commands

### Fetch tweets from a user

```bash
# 1 page of tweets (default, ~20 tweets)
eneet USERNAME --since YYYY-MM-DD

# Up to N tweets via cursor pagination
eneet USERNAME --since YYYY-MM-DD -n 50

# All tweets (unlimited pagination)
eneet USERNAME --since YYYY-MM-DD -n -1

# With date range
eneet USERNAME --since 2024-01-01 --until 2024-06-30 -n -1
```

### Search by keyword

```bash
# Search query
eneet -q "KEYWORD" --since YYYY-MM-DD -n -1

# From specific user with keyword
eneet -q "from:USERNAME KEYWORD" --since YYYY-MM-DD -n -1
```

### Filtering

```bash
# Exclude retweets and replies
eneet USERNAME --no-retweets --no-replies --since YYYY-MM-DD

# Minimum likes threshold
eneet USERNAME --min-likes 100 --since YYYY-MM-DD

# Keyword filters (tweet must contain ALL)
eneet USERNAME -f "AI,GPU" --since YYYY-MM-DD

# Keyword excludes (skip if contains ANY)
eneet USERNAME -e "spam,ad" --since YYYY-MM-DD
```

### Save to file

```bash
# Default filename (posts_USERNAME.jsonl)
eneet USERNAME --since YYYY-MM-DD -o

# Specific file
eneet USERNAME --since YYYY-MM-DD -o output.jsonl
```

### Config file

```bash
eneet -c config.json
```

config.json structure:
```json
{
  "username": "USERNAME",
  "query": null,
  "since_date": "2024-01-01",
  "until_date": null,
  "instance": "https://nitter.net",
  "tweet_limit": -1,
  "filters": [],
  "excludes": [],
  "no_retweets": false,
  "no_replies": false,
  "min_likes": null
}
```

## All Options

| Flag | Description |
|------|-------------|
| `username` | Twitter username (without @) |
| `-q QUERY` | Search query instead of username |
| `-c CONFIG` | Path to config.json |
| `-o [FILE]` | Save to file (default filename if no FILE given) |
| `--since YYYY-MM-DD` | Fetch tweets from this date |
| `--until YYYY-MM-DD` | Fetch tweets until this date |
| `-n N` | Max tweets: default=1 page, `-1`=unlimited, `N`=up to N |
| `-f WORDS` | Only include tweets containing these words (comma-separated) |
| `-e WORDS` | Exclude tweets containing these words (comma-separated) |
| `--no-retweets` | Exclude retweets |
| `--no-replies` | Exclude replies |
| `--min-likes N` | Only include tweets with at least N likes |
| `--instance URL` | Nitter instance URL (default: https://nitter.net) |

## Output Format

Each tweet is a JSON object:

```json
{
  "id": "1234567890",
  "date": "2024-03-15T10:30:00",
  "username": "elonmusk",
  "display_name": "Elon Musk",
  "text": "Tweet text here",
  "likes": 1500,
  "retweets": 200,
  "replies": 80,
  "is_retweet": false,
  "is_reply": false,
  "images": [],
  "videos": [],
  "url": "https://twitter.com/elonmusk/status/1234567890"
}
```

## Practical Examples

```bash
# Get recent AI-related tweets from elonmusk, no retweets
eneet elonmusk --since 2024-01-01 -f "AI" --no-retweets | jq '.text'

# Collect all tweets from a user into a file
eneet yasutaketin --since 2024-01-01 -n -1 -o

# Search keyword from specific user, save to file
eneet -q "from:yasutaketin NBIS" --since 2026-01-01 -n -1 -o nbis_tweets.jsonl

# Count tweets fetched
eneet elonmusk --since 2024-01-01 -n -1 | wc -l

# Extract only text field
eneet elonmusk --since 2024-01-01 | jq -r '.text'
```

## Notes

- Rate limit handling: automatic exponential backoff (up to 15 min) with 5 retries
- Duplicate detection: when saving to file, already-seen IDs are skipped on resume
- If a Nitter instance is down, try `--instance https://nitter.poast.org`
