# X Read-Only Nitter CLI

**Nitter API Client** - Fetch tweets without Twitter API

X Read-Only Nitter CLI is a Python library that allows you to fetch tweets from Twitter/X without using the official Twitter API. It works by scraping Nitter instances (privacy-respecting Twitter frontends).

The Python package and command name remain `eneet` for compatibility.

## Features

- **No Twitter API required** - No API keys, no rate limits
- **CLI tool** - Easy command-line interface for fetching tweets
- **Fetch user tweets** - Get tweets from any public user
- **Search tweets** - Search for tweets by keywords
- **Filter & Exclude** - Filter tweets by keywords, type, or engagement
- **Cursor-based pagination** - Efficiently fetch multiple pages of results
- **Stdout streaming** - Stream JSONL to stdout for pipeline integration
- **JSONL output** - Optionally save tweets to JSONL file

## Installation

```bash
pip install eneet
```

Or install from source:

```bash
git clone https://github.com/ryokobachan/x-readonly-nitter-cli.git
cd x-readonly-nitter-cli
pip install -e .
```

## CLI Usage

After installation, the `eneet` command is available.

### Basic Usage

```bash
# Fetch 1 page of tweets (default) — streams JSON to stdout
eneet elonmusk --since 2024-01-01

# Fetch up to 50 tweets via cursor pagination
eneet elonmusk --since 2024-01-01 -n 50

# Fetch all tweets (unlimited cursor pagination)
eneet elonmusk --since 2024-01-01 -n -1

# Pipe output to another tool
eneet elonmusk --since 2024-01-01 | jq '.text'
```

### Output to File

Without `-o`, tweets stream to **stdout** as JSONL. Use `-o` to save to a file instead.

```bash
# Save to default filename (posts_elonmusk.jsonl)
eneet elonmusk --since 2024-01-01 -o

# Save to specific file
eneet elonmusk --since 2024-01-01 -o elon_tweets.jsonl
```

### Search by Keywords

```bash
# Search for tweets containing keywords
eneet -q "bitcoin OR ethereum" --since 2024-01-01

# Search tweets from a specific user with keywords (unlimited)
eneet -q "from:elonmusk AI" --since 2024-01-01 -n -1
```

### Filter and Exclude

```bash
# Only include tweets containing "AI"
eneet elonmusk -f "AI" --since 2024-01-01

# Only include tweets containing both "AI" AND "GPU"
eneet elonmusk -f "AI,GPU" --since 2024-01-01

# Skip tweets containing "spam" or "ad"
eneet elonmusk -e "spam,ad" --since 2024-01-01

# Exclude retweets and replies
eneet elonmusk --no-retweets --no-replies --since 2024-01-01

# Only include tweets with at least 100 likes
eneet elonmusk --min-likes 100 --since 2024-01-01

# Combine filters
eneet elonmusk -f "AI" -e "spam" --no-retweets --min-likes 50 --since 2024-01-01
```

### Using Config File

```bash
eneet -c config.json
```

**config.json:**
```json
{
  "username": "elonmusk",
  "query": null,
  "until_date": null,
  "since_date": "2024-01-01",
  "instance": "https://nitter.net",
  "filters": ["AI"],
  "excludes": ["spam", "ad"],
  "tweet_limit": -1,
  "no_retweets": false,
  "no_replies": false,
  "min_likes": null
}
```

### All CLI Options

```
eneet [-h] [-q QUERY] [-c CONFIG] [-o [OUTPUT]] [--until UNTIL]
      [--since SINCE] [--instance INSTANCE] [-n N]
      [-f FILTER] [-e EXCLUDE]
      [--no-retweets] [--no-replies] [--min-likes N]
      [username]

positional arguments:
  username              Twitter username to fetch (without @)

options:
  -h, --help            show this help message and exit
  -q, --query           Search query (instead of username)
  -c, --config          Path to config.json file
  -o [OUTPUT]           Output JSONL file. Use -o alone for default filename,
                        -o FILE for specific file. Without -o, streams to stdout.
  --until               Until date (YYYY-MM-DD)
  --since               Since date (YYYY-MM-DD)
  --instance            Nitter instance URL (default: https://nitter.net)
  -n N, --limit N       Max tweets to fetch. Default: 1 page. -1 = unlimited.
  -f, --filter          Only include tweets containing these words (comma-separated)
  -e, --exclude         Skip tweets containing these words (comma-separated)
  --no-retweets         Exclude retweets
  --no-replies          Exclude replies
  --min-likes N         Only include tweets with at least N likes
```

## Python API

### Fetch User Tweets

```python
from eneet import NitterClient

# Initialize client
client = NitterClient()

# Get latest tweets from a user
tweets = client.get_user_tweets("elonmusk", limit=10)

for tweet in tweets:
    print(f"@{tweet.username}: {tweet.text}")
    print(f"Likes: {tweet.likes} | Retweets: {tweet.retweets}")
    print(f"Date: {tweet.date}")
    print("-" * 50)
```

### Get User Information

```python
from eneet import NitterClient

client = NitterClient()

user = client.get_user("elonmusk")

print(f"Name: {user.display_name}")
print(f"Username: @{user.username}")
print(f"Bio: {user.bio}")
print(f"Followers: {user.followers:,}")
```

### Search Tweets

```python
from eneet import NitterClient

client = NitterClient()

# Search for tweets (generator with cursor pagination)
for tweet in client.search("Python programming", limit=50):
    print(f"{tweet.text[:100]}...")
```

### HistoricalFetcher (Programmatic)

```python
from eneet import HistoricalFetcher
from datetime import datetime

# Stream to stdout (default)
fetcher = HistoricalFetcher(
    username="elonmusk",
    since_date=datetime(2024, 1, 1),
    tweet_limit=-1,       # unlimited
    no_retweets=True,
    min_likes=100,
)
fetcher.run()

# Save to file
fetcher = HistoricalFetcher(
    username="elonmusk",
    output_file="elon_tweets.jsonl",
    since_date=datetime(2024, 1, 1),
    filters=["AI"],
    excludes=["spam"],
    tweet_limit=200,
)
fetcher.run()
```

### Use Different Nitter Instance

```python
from eneet import NitterClient

client = NitterClient(instance="https://nitter.poast.org")
tweets = client.get_user_tweets("github", limit=5)
```

## Output Format

Each tweet is output as a single-line JSON object:

```json
{"id": "123456789", "date": "2024-01-15T10:30:00", "username": "elonmusk", "display_name": "Elon Musk", "text": "Tweet content here", "likes": 1000, "retweets": 100, "replies": 50, "is_retweet": false, "is_reply": false, "images": [], "videos": [], "url": "https://twitter.com/elonmusk/status/123456789"}
```

When saving to a file (`-o`), tweets are appended one per line (JSONL format). Re-running with the same output file will skip already-fetched tweet IDs automatically.

## API Reference

### `NitterClient`

Main client class for interacting with Nitter.

#### `__init__(instance=None, timeout=20)`

- `instance` (str, optional): Nitter instance URL. Default: https://nitter.net
- `timeout` (int): Request timeout in seconds. Default: 20

#### `get_user(username: str) -> User`

Fetch user information.

#### `get_user_tweets(username, limit=20, replies=True, retweets=True) -> List[Tweet]`

Fetch tweets from a user's timeline.

#### `search(query: str, limit=None, max_pages=None) -> Iterator[Tweet]`

Search for tweets using cursor-based pagination (generator).

### `HistoricalFetcher`

Class for fetching historical tweets with optional file output.

#### `__init__(...)`

- `username` (str): Twitter username
- `query` (str): Search query (alternative to username)
- `output_file` (str): Output JSONL file path. `None` = stream to stdout (default)
- `until_date` (datetime): Fetch tweets up to this date
- `since_date` (datetime): Fetch tweets from this date
- `tweet_limit` (int): `None` = 1 page, `-1` = unlimited, `N` = up to N tweets
- `instance` (str): Nitter instance URL
- `filters` (list): Words to filter (tweet must contain ALL)
- `excludes` (list): Words to exclude (skip if contains ANY)
- `no_retweets` (bool): Exclude retweets
- `no_replies` (bool): Exclude replies
- `min_likes` (int): Minimum likes threshold

## Important Notes

- **Rate limiting**: The library includes automatic delays to avoid rate limits. On HTTP 429, it backs off exponentially (up to 15 minutes) and retries up to 5 times.
- **Resume capability**: When saving to a file (`-o`), re-running the same command skips already-fetched tweet IDs automatically.
- **Nitter instances** may be down or rate-limited. Try a different `--instance` if needed.
- **Ethical use**: Respect Twitter's terms of service and user privacy.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit pull requests.

## Support

For issues and feature requests, please visit the [GitHub repository](https://github.com/ryokobachan/x-readonly-nitter-cli/issues).

---

Made with love by [@ryokobachan](https://github.com/ryokobachan)
