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
    
    # Start checking from: 2026-02-01 (Current)
    # Go back to: 2010-01-01
    
    current = datetime(2026, 2, 1)
    end_limit = datetime(2010, 1, 1)
    
    periods = []
    while current > end_limit:
        until_date = current
        # Go back ~1 month roughly
        # simple logic: first day of this month -> minus 1 day -> first day of that month
        prev_month_end = until_date.replace(day=1) - timedelta(days=1)
        since_date = prev_month_end.replace(day=1)
        
        since_str = since_date.strftime('%Y-%m-%d')
        until_str = until_date.strftime('%Y-%m-%d')
        
        periods.append((since_str, until_str))
        
        current = since_date
        
    return periods

def main():
    load_ids()
    load_ids()
    # Use auto-selection from updated list
    client = NitterClient()
    
    periods = generate_periods()
    print(f"Generated {len(periods)} monthly periods to search via Nitter.")
    print("Starting historical fetch...")
    
    for i, (since, until) in enumerate(periods):
        # Nitter search query format
        query = f"from:{USERNAME} since:{since} until:{until}"
        print(f"\n[{i+1}/{len(periods)}] 🔍 Searching: {query}")
        
        try:
            total_fetched = 0
            new_saved = 0
            
            # Use search method, no limit
            for tweet in client.search(query, limit=None, max_pages=None):
                saved = save_tweets([tweet], query)
                total_fetched += 1
                new_saved += saved
                
            print(f"   => Found {total_fetched} tweets. Saved {new_saved} new.")
            
            # Sleep between periods to be gentle
            time.sleep(random.uniform(5, 10))
            
        except Exception as e:
            print(f"❌ Error in period {since}~{until}: {e}")
            if "429" in str(e):
                print("Rate limited. Sleeping for 60 seconds...")
                time.sleep(60)
            else:
                time.sleep(10)

if __name__ == "__main__":
    main()
