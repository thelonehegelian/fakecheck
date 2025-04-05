from .twitter_client import TwitterClient
from typing import Optional


class TwitterBotService:
    def __init__(self):
        self.twitter_client = TwitterClient()

    async def handle_fact_check_result(
        self, url: str, fact_check_result: dict
    ) -> Optional[str]:
        """
        Handle fact-checking results and post them to Twitter.

        Args:
            url (str): The URL that was fact-checked
            fact_check_result (dict): The fact-checking results

        Returns:
            Optional[str]: Tweet ID if successful, None if failed
        """
        try:
            # Create a concise message for Twitter
            credibility_score = fact_check_result.get("credibility_score", 0)
            verdict = "likely true" if credibility_score >= 0.7 else "potentially false"

            tweet_text = (
                f"Fact Check Result 🔍\n"
                f"URL: {url}\n"
                f"Verdict: This content appears {verdict}\n"
                f"Credibility Score: {credibility_score:.2f}\n"
                f"#FactCheck #FakeNewsDetection"
            )

            # Post the tweet
            return self.twitter_client.post_tweet(tweet_text)

        except Exception as e:
            # Log the error internally but don't expose details
            print(f"Error handling fact check result: {str(e)}")
            return None

    async def post_daily_stats(self, stats: dict) -> Optional[str]:
        """
        Post daily fact-checking statistics to Twitter.

        Args:
            stats (dict): Daily statistics about fact-checking results

        Returns:
            Optional[str]: Tweet ID if successful, None if failed
        """
        try:
            tweet_text = (
                f"📊 Daily Fact-Checking Stats\n"
                f"Checks performed: {stats.get('total_checks', 0)}\n"
                f"True content: {stats.get('true_content', 0)}\n"
                f"False content: {stats.get('false_content', 0)}\n"
                f"#FactCheck #Statistics"
            )

            return self.twitter_client.post_tweet(tweet_text)

        except Exception as e:
            # Log the error internally but don't expose details
            print(f"Error posting daily stats: {str(e)}")
            return None
