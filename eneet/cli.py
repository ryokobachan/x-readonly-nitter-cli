"""CLI for fetching historical tweets."""

import argparse
import json
import os
import time
import random
from datetime import datetime, timedelta

from .client import NitterClient


class HistoricalFetcher:
    """Fetches historical tweets for a user and saves to JSONL."""

    def __init__(
        self,
        username: str,
        output_file: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        period_days: int = 10,
        instance: str = "https://nitter.net",
    ):
        self.username = username
        self.output_file = output_file or f"posts_{username}.jsonl"
        self.start_date = start_date
        self.end_date = end_date
        self.period_days = period_days
        self.instance = instance
        self.seen_ids = set()

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

    def save_tweet(self, tweet) -> int:
        """Save a single tweet to file. Returns 1 if saved, 0 if duplicate."""
        if not tweet.id or tweet.id in self.seen_ids:
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

    def run(self):
        """Run the historical fetch."""
        print(f"=== Fetching posts for @{self.username} ===")
        print(f"Instance: {self.instance}")
        print(f"Output: {self.output_file}")
        print()

        self.load_existing_ids()
        client = NitterClient(instance=self.instance)

        periods = self.generate_periods()
        if not periods:
            print("No periods to fetch.")
            return

        print(f"Generated {len(periods)} periods to search.")
        print("Starting fetch...\n")

        for i, (since, until) in enumerate(periods):
            query = f"from:{self.username} since:{since} until:{until}"
            print(f"[{i+1}/{len(periods)}] Searching: {query}")

            attempt = 0
            max_attempts = 5
            cumulative_fetched = 0
            cumulative_saved = 0

            while attempt < max_attempts:
                try:
                    for tweet in client.search(query, limit=None, max_pages=None):
                        cumulative_fetched += 1
                        saved = self.save_tweet(tweet)
                        cumulative_saved += saved

                        if saved:
                            text_preview = tweet.text[:50].replace('\n', ' ')
                            print(f"  + {tweet.date.strftime('%Y-%m-%d %H:%M')} - {text_preview}...")

                        if cumulative_fetched % 20 == 0:
                            print(f"  .. fetched {cumulative_fetched}, saved {cumulative_saved} new")

                    print(f"   => Done! Fetched {cumulative_fetched}, saved {cumulative_saved} new.")
                    time.sleep(random.uniform(10, 20))
                    break

                except Exception as e:
                    attempt += 1
                    error_msg = str(e)
                    print(f"Error (Attempt {attempt}/{max_attempts}): {error_msg}")
                    print(f"   (Progress: fetched {cumulative_fetched}, saved {cumulative_saved})")

                    if "429" in error_msg:
                        wait_time = min(60 * (2 ** (attempt - 1)), 900)
                        print(f"Rate limited. Waiting {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        time.sleep(60)
            else:
                print(f"Failed period {since}~{until} after {max_attempts} attempts.")

            print()


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime."""
    if not date_str:
        return None
    return datetime.strptime(date_str, '%Y-%m-%d')


def main():
    parser = argparse.ArgumentParser(
        description="Fetch historical tweets for a user via Nitter"
    )
    parser.add_argument(
        "username",
        nargs="?",
        help="Twitter username to fetch (without @)",
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
        default=10,
        help="Days per search period (default: 10)",
    )
    parser.add_argument(
        "--instance",
        default="https://nitter.net",
        help="Nitter instance URL (default: https://nitter.net)",
    )

    args = parser.parse_args()

    # Load from config if provided
    if args.config:
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
        username = config.get('username')
        start_date = parse_date(config.get('start_date'))
        end_date = parse_date(config.get('end_date'))
        period_days = config.get('period_days', 10)
        instance = config.get('instance', 'https://nitter.net')
    elif args.username:
        username = args.username
        start_date = parse_date(args.start)
        end_date = parse_date(args.end)
        period_days = args.period
        instance = args.instance
    else:
        parser.error("Either username or --config is required")

    output_file = args.output

    fetcher = HistoricalFetcher(
        username=username,
        output_file=output_file,
        start_date=start_date,
        end_date=end_date,
        period_days=period_days,
        instance=instance,
    )
    fetcher.run()


if __name__ == "__main__":
    main()
