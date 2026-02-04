"""Nitter client for fetching tweets."""

import re
import time
import random
from curl_cffi import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Optional, Iterator
from urllib.parse import urljoin

from .models import Tweet, User
from .exceptions import UserNotFoundError, FetchError, ParseError



class NitterClient:
    """Client for fetching tweets from Nitter instances.
    
    Nitter is a free and open source alternative Twitter front-end.
    This client scrapes Nitter to fetch tweets without using Twitter API.
    
    Example:
        >>> from eneet import NitterClient
        >>> client = NitterClient()
        >>> tweets = client.get_user_tweets("elonmusk", limit=10)
        >>> for tweet in tweets:
        ...     print(tweet.text)
    """
    
    DEFAULT_INSTANCES = [
        "https://nitter.net",
        "https://nitter.poast.org",
        "https://nitter.privacydev.net",
    ]
    
    def __init__(self, instance: Optional[str] = None, timeout: int = 20):
        """Initialize Nitter client.
        
        Args:
            instance: Nitter instance URL (default: auto-select from DEFAULT_INSTANCES)
            timeout: Request timeout in seconds (default: 20)
        """
        self.instance = instance or self.DEFAULT_INSTANCES[0]
        self.timeout = timeout
        self.session = requests.Session()
        
        # Use full browser headers to bypass Nitter/Cloudflare protection
        self.session.impersonate = "chrome120"
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Priority': 'u=0, i',
            'Sec-Ch-Ua': '"Chromium";v="144", "Not(A:Brand";v="24", "Google Chrome";v="144"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        })
    
    def _make_request(self, url: str) -> requests.Response:
        """Make HTTP request with error handling.
        
        Args:
            url: URL to fetch
            
        Returns:
            Response object
            
        Raises:
            FetchError: If request fails
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            
            # Raise for standard HTTP errors if we want strict checking, 
            # but Nitter returns 404 for "User not found" which we handle in caller
            if response.status_code >= 400:
                if response.status_code == 404:
                    return response
                raise FetchError(f"HTTP Error {response.status_code} for {url}")
                
            return response
        except requests.RequestsError as e:
            raise FetchError(f"Failed to fetch {url}: {str(e)}")
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse Nitter date string to datetime.
        
        Args:
            date_str: Date string from Nitter
            
        Returns:
            Parsed datetime object
        """
        # Nitter uses format like "Jan 1, 2024 · 10:30 AM UTC"
        try:
            # Remove the " · " separator and "UTC"
            date_str = date_str.replace(' ·', '').replace(' UTC', '').strip()
            return datetime.strptime(date_str, "%b %d, %Y %I:%M %p")
        except Exception:
            # Fallback: return current time if parsing fails
            return datetime.now()
    
    def _parse_count(self, count_str: str) -> int:
        """Parse count string (e.g., '1.2K', '5M') to integer.
        
        Args:
            count_str: Count string
            
        Returns:
            Integer count
        """
        if not count_str:
            return 0
        
        count_str = count_str.strip().upper()
        
        if 'K' in count_str:
            return int(float(count_str.replace('K', '')) * 1000)
        elif 'M' in count_str:
            return int(float(count_str.replace('M', '')) * 1000000)
        else:
            try:
                return int(count_str.replace(',', ''))
            except ValueError:
                return 0
    
    def get_user(self, username: str) -> User:
        """Get user information from Nitter.
        
        Args:
            username: Twitter username (without @)
            
        Returns:
            User object
            
        Raises:
            UserNotFoundError: If user not found
            FetchError: If request fails
        """
        url = f"{self.instance}/{username}"
        response = self._make_request(url)
        
        # Check if user exists
        if "User not found" in response.text or response.status_code == 404:
            raise UserNotFoundError(f"User '{username}' not found")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        try:
            # Parse user profile
            profile = soup.find('div', class_='profile-card')
            if not profile:
                raise ParseError("Could not find profile card")
            
            display_name = profile.find('a', class_='profile-card-fullname')
            display_name = display_name.text.strip() if display_name else username
            
            bio_elem = profile.find('div', class_='profile-bio')
            bio = bio_elem.text.strip() if bio_elem else None
            
            # Parse stats
            stats = soup.find('ul', class_='profile-statlist')
            followers = 0
            following = 0
            tweets_count = 0
            
            if stats:
                for stat in stats.find_all('li', class_='profile-stat'):
                    stat_label = stat.find('span', class_='profile-stat-header')
                    stat_value = stat.find('span', class_='profile-stat-num')
                    
                    if stat_label and stat_value:
                        label = stat_label.text.strip().lower()
                        value = self._parse_count(stat_value.text.strip())
                        
                        if 'tweet' in label:
                            tweets_count = value
                        elif 'following' in label:
                            following = value
                        elif 'follower' in label:
                            followers = value
            
            # Avatar URL
            avatar_elem = profile.find('img', class_='profile-card-avatar')
            avatar_url = urljoin(self.instance, avatar_elem['src']) if avatar_elem else None
            
            return User(
                username=username,
                display_name=display_name,
                bio=bio,
                followers=followers,
                following=following,
                tweets_count=tweets_count,
                avatar_url=avatar_url
            )
        
        except Exception as e:
            if isinstance(e, (UserNotFoundError, FetchError)):
                raise
            raise ParseError(f"Failed to parse user profile: {str(e)}")
    
    def get_pages(
        self,
        username: str,
        start_cursor: Optional[str] = None,
        replies: bool = True,
        retweets: bool = True,
        max_pages: Optional[int] = None
    ) -> Iterator[tuple[List[Tweet], Optional[str]]]:
        """Fetch tweets page by page, yielding (tweets, next_cursor).
        
        This is useful for implementing resume capability.
        
        Args:
            username: Twitter username
            start_cursor: Cursor to start from (for resuming)
            replies: Include replies
            retweets: Include retweets
            max_pages: Max pages to fetch
            
        Yields:
            Tuple of (List[Tweet], next_cursor_string)
        """
        cursor = start_cursor
        pages_fetched = 0
        
        while True:
            # Check page limit
            if max_pages is not None and pages_fetched >= max_pages:
                break

            # Add delay if it's not the first page (or resuming)
            if pages_fetched > 0 or (start_cursor and pages_fetched == 0):
                time.sleep(random.uniform(2.0, 5.0)) # Increased delay for safety

            # Build URL
            if cursor:
                url = f"{self.instance}/{username}?cursor={cursor}"
            else:
                url = f"{self.instance}/{username}"
            
            try:
                response = self._make_request(url)
            except Exception:
                # If request fails, we re-raise so caller can handle/save state
                raise
            
            # Check for user not found
            if pages_fetched == 0 and not cursor and "User not found" in response.text:
                raise UserNotFoundError(f"User '{username}' not found")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            timeline_items = soup.find_all('div', class_='timeline-item')
            
            if not timeline_items:
                break
            
            # Parse tweets on this page
            page_tweets = []
            for item in timeline_items:
                try:
                    tweet = self._parse_tweet(item, username)
                    if not replies and tweet.is_reply: continue
                    if not retweets and tweet.is_retweet: continue
                    page_tweets.append(tweet)
                except Exception:
                    continue
            
            # Find next cursor
            next_cursor = None
            show_more_divs = soup.find_all('div', class_='show-more')
            for sm in show_more_divs:
                link = sm.find('a', href=True)
                if link and 'Load more' in link.text:
                    href = link.get('href', '')
                    if 'cursor=' in href:
                        next_cursor = href.split('cursor=')[-1]
                        break
            
            # Yield current page results
            yield page_tweets, next_cursor
            
            # Prepare for next iteration
            if not next_cursor:
                break
                
            cursor = next_cursor
            pages_fetched += 1

    def get_tweets(
        self, 
        username: str, 
        limit: Optional[int] = None,
        replies: bool = True,
        retweets: bool = True,
        max_pages: Optional[int] = None,
        start_cursor: Optional[str] = None
    ) -> Iterator[Tweet]:
        """Fetch tweets one by one as a generator.
        
        Args:
            username: Twitter username
            limit: Max tweets to yield
            replies: Include replies
            retweets: Include retweets
            max_pages: Max pages to check
            start_cursor: Resume from this cursor
        """
        tweets_yielded = 0
        
        for page_tweets, _ in self.get_pages(
            username, start_cursor, replies, retweets, max_pages
        ):
            for tweet in page_tweets:
                if limit is not None and tweets_yielded >= limit:
                    return
                yield tweet
                tweets_yielded += 1

    def get_user_tweets(
        self, 
        username: str, 
        limit: int = 20,
        replies: bool = True,
        retweets: bool = True,
        max_pages: int = 10
    ) -> List[Tweet]:
        """Fetch tweets as a list (Legacy wrapper)."""
        return list(self.get_tweets(
            username, limit, replies, retweets, max_pages
        ))
    
    def _parse_tweet(self, item_soup: BeautifulSoup, expected_username: str) -> Tweet:
        """Parse a single tweet from HTML.
        
        Args:
            item_soup: BeautifulSoup object of tweet item
            expected_username: Expected username
            
        Returns:
            Tweet object
        """
        # Get tweet link for ID
        tweet_link = item_soup.find('a', class_='tweet-link')
        tweet_id = ''
        tweet_url = ''
        
        if tweet_link and 'href' in tweet_link.attrs:
            href = tweet_link['href']
            tweet_url = urljoin(self.instance, href)
            # Extract ID from URL like "/username/status/1234567890"
            match = re.search(r'/status/(\d+)', href)
            if match:
                tweet_id = match.group(1)
        
        # Get username and display name
        username_elem = item_soup.find('a', class_='username')
        username = username_elem.text.strip().lstrip('@') if username_elem else expected_username
        
        fullname_elem = item_soup.find('a', class_='fullname')
        display_name = fullname_elem.text.strip() if fullname_elem else username
        
        # Get tweet text
        tweet_content = item_soup.find('div', class_='tweet-content')
        text = tweet_content.get_text(separator=' ', strip=True) if tweet_content else ''
        
        # Get date
        tweet_date_elem = item_soup.find('span', class_='tweet-date')
        date_str = tweet_date_elem.find('a')['title'] if tweet_date_elem and tweet_date_elem.find('a') else ''
        tweet_date = self._parse_date(date_str) if date_str else datetime.now()
        
        # Get stats (likes, retweets, replies)
        stats = item_soup.find('div', class_='tweet-stats')
        likes = 0
        retweets = 0
        replies = 0
        
        if stats:
            # Likes
            like_elem = stats.find('span', class_='icon-heart')
            if like_elem and like_elem.parent:
                likes = self._parse_count(like_elem.parent.text.strip())
            
            # Retweets
            rt_elem = stats.find('span', class_='icon-retweet')
            if rt_elem and rt_elem.parent:
                retweets = self._parse_count(rt_elem.parent.text.strip())
            
            # Replies
            reply_elem = stats.find('span', class_='icon-comment')
            if reply_elem and reply_elem.parent:
                replies = self._parse_count(reply_elem.parent.text.strip())
        
        # Check if retweet or reply
        is_retweet = bool(item_soup.find('div', class_='retweet-header'))
        is_reply = 'replying to' in text.lower() or bool(item_soup.find('div', class_='replying-to'))
        
        # Get media
        images = []
        videos = []
        
        attachments = item_soup.find('div', class_='attachments')
        if attachments:
            # Images
            for img in attachments.find_all('img'):
                if 'src' in img.attrs:
                    images.append(urljoin(self.instance, img['src']))
            
            # Videos
            for video in attachments.find_all('video'):
                if 'src' in video.attrs:
                    videos.append(urljoin(self.instance, video['src']))
        
        return Tweet(
            id=tweet_id,
            username=username,
            display_name=display_name,
            text=text,
            date=tweet_date,
            likes=likes,
            retweets=retweets,
            replies=replies,
            is_retweet=is_retweet,
            is_reply=is_reply,
            images=images,
            videos=videos,
            url=tweet_url
        )
    
    def search_tweets(self, query: str, limit: int = 20) -> List[Tweet]:
        """Search for tweets by query.
        
        Args:
            query: Search query
            limit: Maximum number of tweets to fetch
            
        Returns:
            List of Tweet objects
        """
        url = f"{self.instance}/search?f=tweets&q={query}"
        response = self._make_request(url)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        tweets = []
        timeline_items = soup.find_all('div', class_='timeline-item')
        
        for item in timeline_items:
            if len(tweets) >= limit:
                break
            
            try:
                # Extract username from the tweet
                username_elem = item.find('a', class_='username')
                username = username_elem.text.strip().lstrip('@') if username_elem else 'unknown'
                
                tweet = self._parse_tweet(item, username)
                tweets.append(tweet)
            
            except Exception:
                continue
        
        return tweets
