import unittest
from unittest.mock import patch, MagicMock
from ...twitter_bot.twitter_client import TwitterClient


class TestTwitterClient(unittest.TestCase):
    @patch("twitter_bot.twitter_client.tweepy.OAuthHandler")
    @patch("twitter_bot.twitter_client.tweepy.API")
    @patch("twitter_bot.twitter_client.tweepy.Client")
    @patch("twitter_bot.twitter_client.config")
    def setUp(self, mock_config, mock_client, mock_api, mock_auth):
        # Mock the config values
        mock_config.side_effect = lambda x: {
            "TWITTER_API_KEY": "fake_api_key",
            "TWITTER_API_SECRET": "fake_api_secret",
            "TWITTER_ACCESS_TOKEN": "fake_access_token",
            "TWITTER_ACCESS_TOKEN_SECRET": "fake_access_token_secret",
        }[x]

        # Create instance with mocked dependencies
        self.client = TwitterClient()
        self.mock_tweepy_client = mock_client.return_value
        self.mock_tweepy_api = mock_api.return_value

    @patch("twitter_bot.twitter_client.tweepy.Client")
    def test_post_tweet_success(self, mock_client):
        # Arrange
        expected_tweet_id = "12345"
        mock_response = MagicMock()
        mock_response.data = {"id": expected_tweet_id}
        self.mock_tweepy_client.create_tweet.return_value = mock_response

        # Act
        result = self.client.post_tweet("Test tweet")

        # Assert
        self.assertEqual(result, expected_tweet_id)
        self.mock_tweepy_client.create_tweet.assert_called_once_with(text="Test tweet")

    @patch("twitter_bot.twitter_client.tweepy.Client")
    def test_post_tweet_failure(self, mock_client):
        # Arrange
        self.mock_tweepy_client.create_tweet.side_effect = Exception("API Error")

        # Act
        result = self.client.post_tweet("Test tweet")

        # Assert
        self.assertIsNone(result)
        self.mock_tweepy_client.create_tweet.assert_called_once_with(text="Test tweet")

    @patch("twitter_bot.twitter_client.tweepy.Client")
    def test_reply_to_tweet_success(self, mock_client):
        # Arrange
        expected_tweet_id = "67890"
        mock_response = MagicMock()
        mock_response.data = {"id": expected_tweet_id}
        self.mock_tweepy_client.create_tweet.return_value = mock_response

        # Act
        result = self.client.reply_to_tweet("12345", "Test reply")

        # Assert
        self.assertEqual(result, expected_tweet_id)
        self.mock_tweepy_client.create_tweet.assert_called_once_with(
            text="Test reply", in_reply_to_tweet_id="12345"
        )

    @patch("twitter_bot.twitter_client.tweepy.Client")
    def test_reply_to_tweet_failure(self, mock_client):
        # Arrange
        self.mock_tweepy_client.create_tweet.side_effect = Exception("API Error")

        # Act
        result = self.client.reply_to_tweet("12345", "Test reply")

        # Assert
        self.assertIsNone(result)
        self.mock_tweepy_client.create_tweet.assert_called_once_with(
            text="Test reply", in_reply_to_tweet_id="12345"
        )


if __name__ == "__main__":
    unittest.main()
