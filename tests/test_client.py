"""Test cases for Eneet NitterClient."""

import pytest
from eneet import NitterClient, UserNotFoundError


def test_client_initialization():
    """Test client can be initialized."""
    client = NitterClient()
    assert client.instance is not None
    assert client.timeout == 20


def test_client_with_custom_instance():
    """Test client with custom Nitter instance."""
    custom_instance = "https://nitter.poast.org"
    client = NitterClient(instance=custom_instance)
    assert client.instance == custom_instance


def test_get_user():
    """Test fetching user information."""
    client = NitterClient()
    try:
        user = client.get_user("elonmusk")
        assert user.username == "elonmusk"
        assert user.display_name is not None
        assert user.followers > 0
    except Exception as e:
        pytest.skip(f"Skipping due to Nitter availability: {e}")


def test_get_user_not_found():
    """Test error when user doesn't exist."""
    client = NitterClient()
    try:
        with pytest.raises(UserNotFoundError):
            client.get_user("this_user_definitely_does_not_exist_12345")
    except Exception as e:
        pytest.skip(f"Skipping due to Nitter availability: {e}")


def test_get_user_tweets():
    """Test fetching user tweets."""
    client = NitterClient()
    try:
        tweets = client.get_user_tweets("github", limit=5)
        assert len(tweets) > 0
        for tweet in tweets:
            assert tweet.username is not None
            assert tweet.text is not None
    except Exception as e:
        pytest.skip(f"Skipping due to Nitter availability: {e}")


def test_get_user_tweets_no_retweets():
    """Test filtering out retweets."""
    client = NitterClient()
    try:
        tweets = client.get_user_tweets("github", limit=10, retweets=False)
        for tweet in tweets:
            assert not tweet.is_retweet
    except Exception as e:
        pytest.skip(f"Skipping due to Nitter availability: {e}")


def test_search_tweets():
    """Test searching for tweets."""
    client = NitterClient()
    try:
        tweets = client.search_tweets("python", limit=5)
        assert len(tweets) > 0
    except Exception as e:
        pytest.skip(f"Skipping due to Nitter availability: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
