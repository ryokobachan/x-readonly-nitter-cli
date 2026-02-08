"""CLI for fetching historical tweets."""

import argparse
import json
import os
import time
import random
from datetime import datetime, timedelta
from typing import List, Optional

from .client import NitterClient


class HistoricalFetcher:
    """Fetches historical tweets for a user and saves to JSONL."""

    def __init__(
        self,
        username: str = None,
        query: str = None,
        output_file: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        period_days: int = 10,
        instance: str = "https://nitter.net",
        filters: List[str] = None,
        excludes: List[str] = None,
    ):
        self.username = username
        self.query = query
        self.output_file = output_file or self._default_output_file()
        self.start_date = start_date
        self.end_date = end_date
        self.period_days = period_days
        self.instance = instance
        self.filters = filters or []
        self.excludes = excludes or []
        self.seen_ids = set()

    def _default_output_file(self) -> str:
        if self.username:
            return f"posts_{self.username}.jsonl"
        elif self.query:
            # Sanitize query for filename
            safe_query = "".join(c if c.isalnum() else "_" for c in self.query[:30])
            return f"search_{safe_query}.jsonl"
        return "posts.jsonl"

    def load_existing_ids(self):
        """Load existing IDs from output file."""
        if not os.path.exists(self.output_file):
            return
        with open(self.output_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get('id'):
                        self.seen_ids.add(data['id'])
                except:
                    pass
        print(f"Loaded {len(self.seen_ids)} existing IDs from {self.output_file}")

    def should_save(self, tweet) -> bool:
        """Check if tweet passes filter/exclude rules."""
        text_lower = tweet.text.lower()

        # Check filters (must contain ALL)
        for f in self.filters:
            if f.lower() not in text_lower:
                return False

        # Check excludes (must NOT contain ANY)
        for e in self.excludes:
            if e.lower() in text_lower:
                return False

        return True

    def save_tweet(self, tweet) -> int:
        """Save a single tweet to file. Returns 1 if saved, 0 if skipped."""
        if not tweet.id or tweet.id in self.seen_ids:
            return 0

        if not self.should_save(tweet):
            return 0

        self.seen_ids.add(tweet.id)

        data = {
            'id': tweet.id,
            'date': tweet.date.isoformat(),
            'username': tweet.username,
            'display_name': tweet.display_name,
            'text': tweet.text,
            'likes': tweet.likes,
            'retweets': tweet.retweets,
            'replies': tweet.replies,
            'is_retweet': tweet.is_retweet,
            'is_reply': tweet.is_reply,
            'images': tweet.images,
            'videos': tweet.videos,
            'url': tweet.url,
        }

        with open(self.output_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
            f.flush()
        return 1

    def get_oldest_date(self) -> datetime:
        """Get oldest date from existing data."""
        if not os.path.exists(self.output_file):
            return None
        oldest = None
        with open(self.output_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    date = datetime.fromisoformat(data['date'])
                    if oldest is None or date < oldest:
                        oldest = date
                except:
                    pass
        return oldest

    def generate_periods(self) -> list:
        """Generate search periods going backwards."""
        oldest = self.get_oldest_date()

        # Determine start point
        if self.start_date:
            current = self.start_date
            print(f"Using start_date: {self.start_date.strftime('%Y-%m-%d')}")
        elif oldest:
            next_day = (oldest + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            current = next_day
            print(f"Oldest existing data: {oldest.strftime('%Y-%m-%d %H:%M')}")
            print(f"Will fetch until:{current.strftime('%Y-%m-%d')} (exclusive)")
        else:
            current = datetime.now()
            print("No existing data found. Starting from today.")

        # Determine end point
        end_limit = self.end_date if self.end_date else datetime(1970, 1, 1)
        if self.end_date:
            print(f"End limit: {self.end_date.strftime('%Y-%m-%d')}")
        else:
            print("End limit: unlimited")

        periods = []
        while current > end_limit:
            until_date = current
            since_date = until_date - timedelta(days=self.period_days)

            if since_date < end_limit:
                since_date = end_limit

            periods.append((
                since_date.strftime('%Y-%m-%d'),
                until_date.strftime('%Y-%m-%d'),
            ))
            current = since_date

        return periods

    def build_query(self, since: str, until: str) -> str:
        """Build search query with date range."""
        if self.username:
            base = f"from:{self.username}"
        elif self.query:
            base = self.query
        else:
            raise ValueError("Either username or query is required")

        return f"{base} since:{since} until:{until}"

    def run(self):
        """Run the historical fetch."""
        if self.username:
            print(f"=== Fetching posts for @{self.username} ===")
        elif self.query:
            print(f"=== Searching: {self.query} ===")

        print(f"Instance: {self.instance}")
        print(f"Output: {self.output_file}")

        if self.filters:
            print(f"Filters (must contain): {self.filters}")
        if self.excludes:
            print(f"Excludes (must NOT contain): {self.excludes}")

        print()

        self.load_existing_ids()
        client = NitterClient(instance=self.instance)

        periods = self.generate_periods()
        if not periods:
            print("No periods to fetch.")
            return

        print(f"Generated {len(periods)} periods to search.")
        print("Starting fetch...\n")

        total_saved = 0
        for i, (since, until) in enumerate(periods):
            query = self.build_query(since, until)

            attempt = 0
            max_attempts = 5
            cumulative_fetched = 0
            cumulative_saved = 0
            last_date = None
            status_width = 80  # For clearing line

            while attempt < max_attempts:
                try:
                    for tweet in client.search(query, limit=None, max_pages=None):
                        cumulative_fetched += 1
                        saved = self.save_tweet(tweet)
                        cumulative_saved += saved

                        # Update status line with current date
                        current_date = tweet.date.strftime('%Y-%m-%d')
                        if current_date != last_date:
                            last_date = current_date
                            status = f"[{i+1}/{len(periods)}] {since} ~ {until} | {current_date} | saved: {total_saved + cumulative_saved}"
                            print(f"\r{status:<{status_width}}", end="", flush=True)

                    total_saved += cumulative_saved
                    status = f"[{i+1}/{len(periods)}] {since} ~ {until} | done | +{cumulative_saved} (total: {total_saved})"
                    print(f"\r{status:<{status_width}}")
                    time.sleep(random.uniform(15, 25))
                    break

                except Exception as e:
                    attempt += 1
                    error_msg = str(e)

                    if "429" in error_msg:
                        wait_time = min(60 * (2 ** (attempt - 1)), 900)
                        print(f"\n  429 Rate limited ({attempt}/{max_attempts}): {error_msg}")
                        print(f"  Resetting session and waiting {wait_time}s...")
                        client.reset_session()
                        time.sleep(wait_time)
                    else:
                        print(f"\n  Error ({attempt}/{max_attempts}): {error_msg}")
                        time.sleep(60)
            else:
                print(f"\n  Failed {since}~{until} after {max_attempts} attempts.")


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime."""
    if not date_str:
        return None
    return datetime.strptime(date_str, '%Y-%m-%d')


def parse_list(value: str) -> List[str]:
    """Parse comma-separated string to list."""
    if not value:
        return []
    return [v.strip() for v in value.split(',') if v.strip()]


def main():
    parser = argparse.ArgumentParser(
        description="Fetch historical tweets via Nitter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch all tweets from a user
  eneet elonmusk --end 2024-01-01

  # Search for keywords
  eneet -q "bitcoin OR ethereum" --end 2024-01-01

  # Fetch with filters (must contain "AI")
  eneet elonmusk --filter "AI" --end 2024-01-01

  # Fetch excluding certain words
  eneet elonmusk --exclude "spam,ad" --end 2024-01-01

  # Use config file
  eneet -c config.json
        """
    )
    parser.add_argument(
        "username",
        nargs="?",
        help="Twitter username to fetch (without @)",
    )
    parser.add_argument(
        "-q", "--query",
        help="Search query (instead of username)",
    )
    parser.add_argument(
        "-c", "--config",
        help="Path to config.json file",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output JSONL file (default: posts_{username}.jsonl)",
    )
    parser.add_argument(
        "--start",
        help="Start date (YYYY-MM-DD) - fetch from this date backwards",
    )
    parser.add_argument(
        "--end",
        help="End date (YYYY-MM-DD) - stop fetching at this date",
    )
    parser.add_argument(
        "--period",
        type=int,
        default=1,
        help="Days per search period (default: 1)",
    )
    parser.add_argument(
        "--instance",
        default="https://nitter.net",
        help="Nitter instance URL (default: https://nitter.net)",
    )
    parser.add_argument(
        "-f", "--filter",
        help="Filter: only save tweets containing these words (comma-separated)",
    )
    parser.add_argument(
        "-e", "--exclude",
        help="Exclude: skip tweets containing these words (comma-separated)",
    )

    args = parser.parse_args()

    # Load from config if provided
    if args.config:
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
        username = config.get('username')
        query = config.get('query')
        start_date = parse_date(config.get('start_date'))
        end_date = parse_date(config.get('end_date'))
        period_days = config.get('period_days', 10)
        instance = config.get('instance', 'https://nitter.net')
        filters = config.get('filters', [])
        excludes = config.get('excludes', [])
        output_file = config.get('output') or args.output
    else:
        username = args.username
        query = args.query
        start_date = parse_date(args.start)
        end_date = parse_date(args.end)
        period_days = args.period
        instance = args.instance
        filters = parse_list(args.filter)
        excludes = parse_list(args.exclude)
        output_file = args.output

    if not username and not query:
        parser.error("Either username, --query, or --config is required")

    fetcher = HistoricalFetcher(
        username=username,
        query=query,
        output_file=output_file,
        start_date=start_date,
        end_date=end_date,
        period_days=period_days,
        instance=instance,
        filters=filters,
        excludes=excludes,
    )
    fetcher.run()


if __name__ == "__main__":
    main()
