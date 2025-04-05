import unittest
from unittest.mock import patch, MagicMock
from ...twitter_bot.bot_service import TwitterBotService  # Changed import


class TestTwitterBotService(unittest.TestCase):
    def setUp(self):
        self.bot_service = TwitterBotService()
        # Mock the TwitterClient instance
        self.bot_service.twitter_client = MagicMock()

    async def test_handle_fact_check_result_true_content(self):
        # Arrange
        url = "https://example.com/article"
        fact_check_result = {
            "credibility_score": 0.8,
            "analysis": "Content appears to be true",
        }
        expected_tweet_id = "12345"
        self.bot_service.twitter_client.post_tweet.return_value = expected_tweet_id

        # Act
        result = await self.bot_service.handle_fact_check_result(url, fact_check_result)

        # Assert
        self.assertEqual(result, expected_tweet_id)
        self.bot_service.twitter_client.post_tweet.assert_called_once()
        tweet_text = self.bot_service.twitter_client.post_tweet.call_args[0][0]
        self.assertIn("likely true", tweet_text)
        self.assertIn(url, tweet_text)
        self.assertIn("0.80", tweet_text)

    async def test_handle_fact_check_result_false_content(self):
        # Arrange
        url = "https://example.com/article"
        fact_check_result = {
            "credibility_score": 0.3,
            "analysis": "Content appears to be false",
        }
        expected_tweet_id = "12345"
        self.bot_service.twitter_client.post_tweet.return_value = expected_tweet_id

        # Act
        result = await self.bot_service.handle_fact_check_result(url, fact_check_result)

        # Assert
        self.assertEqual(result, expected_tweet_id)
        self.bot_service.twitter_client.post_tweet.assert_called_once()
        tweet_text = self.bot_service.twitter_client.post_tweet.call_args[0][0]
        self.assertIn("potentially false", tweet_text)
        self.assertIn(url, tweet_text)
        self.assertIn("0.30", tweet_text)

    async def test_handle_fact_check_result_failure(self):
        # Arrange
        url = "https://example.com/article"
        fact_check_result = {"credibility_score": 0.8}
        self.bot_service.twitter_client.post_tweet.side_effect = Exception("API Error")

        # Act
        result = await self.bot_service.handle_fact_check_result(url, fact_check_result)

        # Assert
        self.assertIsNone(result)
        self.bot_service.twitter_client.post_tweet.assert_called_once()

    async def test_post_daily_stats_success(self):
        # Arrange
        stats = {"total_checks": 100, "true_content": 75, "false_content": 25}
        expected_tweet_id = "67890"
        self.bot_service.twitter_client.post_tweet.return_value = expected_tweet_id

        # Act
        result = await self.bot_service.post_daily_stats(stats)

        # Assert
        self.assertEqual(result, expected_tweet_id)
        self.bot_service.twitter_client.post_tweet.assert_called_once()
        tweet_text = self.bot_service.twitter_client.post_tweet.call_args[0][0]
        self.assertIn("100", tweet_text)
        self.assertIn("75", tweet_text)
        self.assertIn("25", tweet_text)

    async def test_post_daily_stats_failure(self):
        # Arrange
        stats = {"total_checks": 100, "true_content": 75, "false_content": 25}
        self.bot_service.twitter_client.post_tweet.side_effect = Exception("API Error")

        # Act
        result = await self.bot_service.post_daily_stats(stats)

        # Assert
        self.assertIsNone(result)
        self.bot_service.twitter_client.post_tweet.assert_called_once()


if __name__ == "__main__":
    unittest.main()
