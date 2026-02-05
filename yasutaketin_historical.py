import json
import os
import time
import random
from datetime import datetime, timedelta
from dataclasses import asdict
from eneet import NitterClient

USERNAME = "yasutaketin"
DATA_FILE = f"tweets_{USERNAME}.jsonl"

# In-memory ID tracking
SEEN_IDS = set()

def load_ids():
    print(f"Loading existing IDs from {DATA_FILE}...")
    if not os.path.exists(DATA_FILE): return
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                data = json.loads(line)
                if data.get('id'): SEEN_IDS.add(data['id'])
            except: pass
    print(f"Loaded {len(SEEN_IDS)} valid IDs.")

def save_tweets(tweets, query):
    count = 0
    with open(DATA_FILE, 'a', encoding='utf-8') as f:
        for tweet in tweets:
            if not tweet.id or tweet.id in SEEN_IDS: continue
            SEEN_IDS.add(tweet.id)
            
            data = asdict(tweet)
            data['date'] = tweet.date.isoformat()
            data['fetch_query'] = query 
            
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
            count += 1
    return count

def generate_periods():
    """
    Generate monthly search periods.
    Adjust START_DATE and END_DATE as needed.
    """
    # Latest tweets are usually fetched by the main scraper.
    # This script is for historical backfill.
    
    # Start checking from: Today
    # Go back to: 2025-01-01
    
    current = datetime.now()
    end_limit = datetime(2025, 1, 1)
    
    periods = []
    while current > end_limit:
        until_date = current
        # Go back 10 days to ensure we capture everything without hitting pagination limits
        since_date = until_date - timedelta(days=10)
        
        since_str = since_date.strftime('%Y-%m-%d')
        until_str = until_date.strftime('%Y-%m-%d')
        
        periods.append((since_str, until_str))
        
        current = since_date
        
    return periods


COMPLETED_PERIODS_FILE = "completed_periods.txt"

def load_completed_periods():
    if not os.path.exists(COMPLETED_PERIODS_FILE):
        return set()
    with open(COMPLETED_PERIODS_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def mark_period_completed(period_str):
    with open(COMPLETED_PERIODS_FILE, 'a', encoding='utf-8') as f:
        f.write(period_str + '\n')

def main():
    load_ids()
    completed_periods = load_completed_periods()
    print(f"Loaded {len(completed_periods)} completed periods.")
    
    # STRICTLY use nitter.net as requested
    client = NitterClient(instance="https://nitter.net")
    
    # Generate periods
    periods = generate_periods()
    print(f"Generated {len(periods)} monthly periods to search via nitter.net.")
    print("Starting historical fetch with strict rate limiting...")
    
    for i, (since, until) in enumerate(periods):
        period_key = f"{since}_{until}"
        if period_key in completed_periods:
            print(f"[{i+1}/{len(periods)}] ✅ Skipping completed period: {since} ~ {until}")
            continue

        query = f"from:{USERNAME} since:{since} until:{until}"
        print(f"\n[{i+1}/{len(periods)}] 🔍 Searching: {query}")
        
        attempt = 0
        max_attempts = 5
        
        while attempt < max_attempts:
            try:
                total_fetched = 0
                new_saved = 0
                
                # Fetch
                for tweet in client.search(query, limit=None, max_pages=None):
                    saved = save_tweets([tweet], query)
                    total_fetched += 1
                    new_saved += saved
                    
                    # Be very gentle during fetch loop too
                    if total_fetched % 10 == 0:
                        print(f"  .. fetched {total_fetched} tweets")
                        time.sleep(2)
                
                print(f"   => Found {total_fetched} tweets. Saved {new_saved} new.")
                
                # Mark as completed
                mark_period_completed(period_key)
                
                # Success! Sleep and move to next period
                time.sleep(random.uniform(10, 20))
                break
                
            except Exception as e:
                attempt += 1
                error_msg = str(e)
                print(f"❌ Error in period {since}~{until} (Attempt {attempt}/{max_attempts}): {error_msg}")
                
                # Check for 429
                if "429" in error_msg:
                    # Exponential backoff for Rate Limits
                    # 1st try: 30s, 2nd: 60s, 3rd: 120s...
                    wait_time = 30 * (2 ** (attempt - 1))
                    if wait_time > 900: wait_time = 900 # Cap at 15 mins
                    
                    print(f"⚠️ RATE LIMITED on nitter.net. Sleeping for {wait_time} seconds ({wait_time/60:.1f} min)...")
                    # Show countdown or just sleep
                    time.sleep(wait_time)
                else:
                    # Other errors
                    time.sleep(30)
        else:
            print(f"💀 Failed to fetch period {since}~{until} after {max_attempts} attempts. Skipping.")

if __name__ == "__main__":
    main()
