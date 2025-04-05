import tweepy
from typing import Optional
from decouple import config


class TwitterClient:
    def __init__(self):
        # Load Twitter API credentials from environment variables
        self.api_key = config("TWITTER_API_KEY")
        self.api_secret = config("TWITTER_API_SECRET")
        self.access_token = config("TWITTER_ACCESS_TOKEN")
        self.access_token_secret = config("TWITTER_ACCESS_TOKEN_SECRET")

        # Initialize the Twitter API client
        self.auth = tweepy.OAuthHandler(self.api_key, self.api_secret)
        self.auth.set_access_token(self.access_token, self.access_token_secret)
        self.api = tweepy.API(self.auth)
        self.client = tweepy.Client(
            consumer_key=self.api_key,
            consumer_secret=self.api_secret,
            access_token=self.access_token,
            access_token_secret=self.access_token_secret,
        )

    def post_tweet(self, text: str) -> Optional[str]:
        """
        Post a tweet with the given text.

        Args:
            text (str): The text content of the tweet

        Returns:
            Optional[str]: Tweet ID if successful, None if failed
        """
        try:
            tweet = self.client.create_tweet(text=text)
            return tweet.data["id"]
        except Exception as e:
            # Log the error internally but don't expose details
            print(f"Error posting tweet: {str(e)}")
            return None

    def reply_to_tweet(self, tweet_id: str, text: str) -> Optional[str]:
        """
        Reply to a specific tweet.

        Args:
            tweet_id (str): The ID of the tweet to reply to
            text (str): The text content of the reply

        Returns:
            Optional[str]: Reply tweet ID if successful, None if failed
        """
        try:
            reply = self.client.create_tweet(text=text, in_reply_to_tweet_id=tweet_id)
            return reply.data["id"]
        except Exception as e:
            # Log the error internally but don't expose details
            print(f"Error replying to tweet: {str(e)}")
            return None
