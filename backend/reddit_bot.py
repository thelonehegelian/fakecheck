
import asyncio
import logging
import time
from typing import Optional

import praw
from praw.models import Comment, Submission

from src.core.config import get_settings
from src.models.requests import FactCheckRequest
from src.services.fact_checker import FactCheckService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("reddit_bot")


class RedditBot:
    def __init__(self):
        self.settings = get_settings()
        
        # Check required credentials
        if not all([
            self.settings.reddit_client_id,
            self.settings.reddit_client_secret,
            self.settings.reddit_username,
            self.settings.reddit_password,
        ]):
            raise ValueError("Missing Reddit API credentials in configuration")

        self.reddit = praw.Reddit(
            client_id=self.settings.reddit_client_id,
            client_secret=self.settings.reddit_client_secret,
            user_agent=self.settings.reddit_user_agent,
            username=self.settings.reddit_username,
            password=self.settings.reddit_password,
        )
        
        self.subreddit_name = self.settings.reddit_subreddit
        self.fact_checker = FactCheckService(self.settings)

        # Deduplication and rate limiting
        self.replied_comments_file = "replied_comments.txt"
        self.replied_comments = set()
        self._load_replied_comments()
        self.user_last_request = {}

    def _load_replied_comments(self):
        import os
        if os.path.exists(self.replied_comments_file):
            try:
                with open(self.replied_comments_file, "r") as f:
                    self.replied_comments = set(line.strip() for line in f if line.strip())
            except Exception as e:
                logger.error(f"Failed to load replied comments: {e}")

    def _save_replied_comment(self, comment_id: str):
        self.replied_comments.add(comment_id)
        try:
            with open(self.replied_comments_file, "a") as f:
                f.write(f"{comment_id}\n")
        except Exception as e:
            logger.error(f"Failed to save replied comment: {e}")

    async def process_comment(self, comment: Comment):
        """Process a single comment."""
        try:
            body = comment.body.lower()
            if "!fakecheck" not in body:
                return

            # Check deduplication
            if comment.id in self.replied_comments:
                return

            # Check user rate limit (30 seconds between requests)
            author = str(comment.author)
            now = time.time()
            if author in self.user_last_request:
                time_since_last = now - self.user_last_request[author]
                if time_since_last < 30:
                    logger.warning(f"User {author} is rate-limited. Time since last: {time_since_last:.1f}s")
                    comment.reply(f"Please wait {30 - time_since_last:.0f} seconds before making another request.")
                    self._save_replied_comment(comment.id)
                    return
            
            self.user_last_request[author] = now
            logger.info(f"Command found in comment {comment.id} by {comment.author}")

            # Get content to check
            content_to_check = self._get_content_to_check(comment)
            if not content_to_check:
                logger.warning(f"No content found to check for comment {comment.id}")
                return

            logger.info(f"Checking content: {content_to_check[:100]}...")
            
            # Send "Processing" reply to let user know we picked it up
            # PRAW is synchronous, so no await here
            reply_msg = comment.reply("Processing... I'm researching this claim. This may take a minute.")
            
            # Perform fact check
            # This IS async, so we await it
            request = FactCheckRequest(news=content_to_check)
            result = await self.fact_checker.check_news(request)
            
            # Format and send reply
            reply_text = self._format_reply(result)
            
            # Edit the processing message with the final result
            reply_msg.edit(reply_text)
            self._save_replied_comment(comment.id)
            logger.info(f"Successfully processed comment {comment.id}")

        except Exception as e:
            logger.error(f"Error processing comment {comment.id}: {str(e)}")
            try:
                self._save_replied_comment(comment.id)
            except:
                pass

    def _get_content_to_check(self, comment: Comment) -> Optional[str]:
        """Extract text from parent comment or submission."""
        # Check if it's a reply to another comment
        if not comment.is_root:
            parent = comment.parent()
            # If parent is a comment, we need to fetch it if it's not fully loaded (lazy loading)
            if not isinstance(parent, Comment):
                 # PRAW handles lazy loading usually, but explicit refresh ensures we have body
                 parent.refresh()
            return parent.body
        
        # If it's a top-level comment, check the submission
        submission = comment.submission
        if submission.selftext:
            return submission.selftext
        elif submission.url:
            # If it's a link post, we can't easily check the content without scraping the URL.
            # But our fact checker accepts text. We could pass the URL as text and hope extraction works?
            # Or just pass the title + URL.
            return f"{submission.title}\n{submission.url}"
        else:
            return submission.title

    def _format_reply(self, result: dict) -> str:
        """Format the fact-check result into a Markdown reply."""
        
        rating = result.get("fake_news_rating", "N/A")
        # Map rating to a emoji or text
        rating_map = {
            1: "True ✅",
            2: "Likely True 🟢",
            3: "Unverified / Mixed 🟡",
            4: "Likely Fake 🔴",
            5: "Fake ❌"
        }
        rating_str = rating_map.get(rating, f"Rating: {rating}")
        
        confidence = result.get("confidence_score", 0)
        confidence_str = f"{confidence * 100:.0f}%"
        
        reply = f"## FakeCheck Result: {rating_str}\n\n"
        reply += f"**Confidence:** {confidence_str}\n\n"
        
        explanation = result.get("fake_news_explanation") or result.get("true_news_explanation")
        if explanation:
            reply += f"### Analysis\n{explanation}\n\n"
        
        risk_factors = result.get("risk_factors", [])
        if risk_factors:
            reply += "### Risk Factors\n"
            for factor in risk_factors:
                reply += f"- {factor}\n"
            reply += "\n"
            
        citations = result.get("citations", [])
        if citations:
            reply += "### Sources\n"
            for i, cite in enumerate(citations[:3], 1):
                if isinstance(cite, str):
                     reply += f"{i}. {cite}\n"
                elif isinstance(cite, dict) and "url" in cite:
                     reply += f"{i}. [{cite.get('title', 'Link')}]({cite['url']})\n"
        
        reply += "\n---\n*I am a bot. beep boop.*"
        return reply

    def run(self, loop=None):
        """Main loop to monitor stream."""
        logger.info(f"Starting Reddit Bot on /r/{self.subreddit_name}...")
        try:
            for comment in self.subreddit.stream.comments(skip_existing=True):
                # Quick pre-checks before triggering processing
                body = comment.body.lower()
                if "!fakecheck" not in body or comment.id in self.replied_comments:
                    continue

                # Run the async comment processing safely
                if loop and loop.is_running():
                    asyncio.run_coroutine_threadsafe(self.process_comment(comment), loop)
                else:
                    asyncio.run(self.process_comment(comment))
        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
        except Exception as e:
            logger.error(f"Critical bot error: {str(e)}")
    
    def run_in_background(self):
        """Run the bot in a separate thread."""
        import threading
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
            
        thread = threading.Thread(target=self.run, args=(loop,), daemon=True)
        thread.start()
        return thread

    @property
    def subreddit(self):
        return self.reddit.subreddit(self.subreddit_name)


if __name__ == "__main__":
    bot = RedditBot()
    bot.run()
