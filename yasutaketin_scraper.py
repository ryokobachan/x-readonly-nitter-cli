import json
import os
import time
from dataclasses import asdict
from eneet import NitterClient
from eneet.exceptions import FetchError, UserNotFoundError

# Configuration
USERNAME = "yasutaketin"
DATA_FILE = f"tweets_{USERNAME}.jsonl"
PROGRESS_FILE = f"progress_{USERNAME}.json"

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"cursor": None, "total_tweets": 0}

def save_progress(cursor, total_tweets):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump({"cursor": cursor, "total_tweets": total_tweets}, f)

def save_tweets(tweets):
    with open(DATA_FILE, 'a', encoding='utf-8') as f:
        for tweet in tweets:
            # dataclass to dict
            data = asdict(tweet)
            # convert datetime to string for json serialization
            data['date'] = tweet.date.isoformat()
            # write as newline-delimited json
            f.write(json.dumps(data, ensure_ascii=False) + '\n')

def main():
    client = NitterClient()
    progress = load_progress()
    cursor = progress["cursor"]
    total = progress["total_tweets"]
    
    print(f"==================================================")
    print(f" Nitter Scraper for @{USERNAME}")
    print(f"==================================================")
    print(f"Resuming from cursor: {cursor if cursor else 'START'}")
    print(f"Tweets collected so far: {total}")
    print(f"Data file: {DATA_FILE}")
    print(f"Progress file: {PROGRESS_FILE}")
    print(f"--------------------------------------------------")
    
    try:
        # Fetch page by page (infinite scrolling)
        for tweets, next_cursor in client.get_pages(
            USERNAME, 
            start_cursor=cursor,
            replies=True, 
            retweets=True,
            max_pages=None # Infinite
        ):
            if not tweets:
                print(f"No tweets found on this page. (Cursor: {cursor})")
            
            # Save data immediately
            save_tweets(tweets)
            total += len(tweets)
            
            # Update progress
            save_progress(next_cursor, total)
            
            # Log progress
            cursor_short = next_cursor[:20] + '...' if next_cursor else 'None'
            print(f"Fetched {len(tweets)} tweets. Total: {total}. Next cursor: {cursor_short}")
            
            if not next_cursor:
                print("\n🎉 End of timeline reached!")
                break
                
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped by user.")
        print("Progress has been saved. Run script again to resume exactly where you left off.")
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print("Progress has been saved. Run script again to resume.")

if __name__ == "__main__":
    main()
