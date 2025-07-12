
import os
import time
import requests
from requests_oauthlib import OAuth1

# --- Twitter API Credentials ---
# Make sure to set these as environment variables for security
# You can get these from the Twitter Developer Portal (https://developer.twitter.com)
# See the langchain-docs/twitter-bot-docs.md for a guide on how to get these.
CONSUMER_KEY = os.environ.get("TWITTER_CONSUMER_KEY")
CONSUMER_SECRET = os.environ.get("TWITTER_CONSUMER_SECRET")
ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

# --- Bot Configuration ---
# The bot's Twitter handle (without the @)
BOT_USERNAME = "YourBotUsername" # <--- IMPORTANT: CHANGE THIS
# The message to reply with
REPLY_MESSAGE = "Hello! You summoned me."
# How often to check for new mentions (in seconds)
CHECK_INTERVAL = 60
# File to store the ID of the last tweet replied to
LAST_TWEET_ID_FILE = "last_tweet_id.txt"


def get_last_tweet_id():
    """Reads the last replied tweet ID from a file."""
    if not os.path.exists(LAST_TWEET_ID_FILE):
        return None
    with open(LAST_TWEET_ID_FILE, "r") as f:
        return f.read().strip()


def save_last_tweet_id(tweet_id):
    """Saves the last replied tweet ID to a file."""
    with open(LAST_TWEET_ID_FILE, "w") as f:
        f.write(str(tweet_id))


def search_mentions(since_id):
    """
    Searches for recent mentions of the bot.
    Docs: https://developer.twitter.com/en/docs/twitter-api/tweets/search/api-reference/get-tweets-search-recent
    """
    print("Searching for new mentions...")
    search_url = "https://api.x.com/2/tweets/search/recent"
    
    # Query to find tweets that mention the bot, are not retweets, and are not replies from the bot itself.
    query = f"@{BOT_USERNAME} -is:retweet -from:{BOT_USERNAME}"
    
    params = {"query": query, "tweet.fields": "author_id"}
    if since_id:
        params["since_id"] = since_id

    auth = OAuth1(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    
    response = requests.get(search_url, auth=auth, params=params)
    
    if response.status_code != 200:
        print(f"Error searching for tweets: {response.status_code} {response.text}")
        return None
        
    return response.json()


def post_reply(tweet_id, message):
    """
    Posts a reply to a specific tweet.
    Docs: https://developer.twitter.com/en/docs/twitter-api/tweets/manage-tweets/api-reference/post-tweets
    """
    print(f"Replying to tweet {tweet_id}...")
    post_url = "https://api.x.com/2/tweets"
    
    payload = {
        "text": message,
        "reply": {
            "in_reply_to_tweet_id": tweet_id
        }
    }
    
    auth = OAuth1(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    
    response = requests.post(post_url, auth=auth, json=payload)
    
    if response.status_code == 201:
        print("Reply posted successfully!")
    else:
        print(f"Error posting reply: {response.status_code} {response.text}")


def run_bot():
    """Main function to run the bot."""
    
    if not all([CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
        print("Error: Twitter API credentials are not set.")
        print("Please set TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, TWITTER_ACCESS_TOKEN, and TWITTER_ACCESS_TOKEN_SECRET as environment variables.")
        return

    if BOT_USERNAME == "YourBotUsername":
        print("Error: Please change the BOT_USERNAME in the script to your bot's actual Twitter handle.")
        return

    print(f"Starting Twitter Bot for @{BOT_USERNAME}...")
    
    last_id = get_last_tweet_id()
    
    while True:
        mentions = search_mentions(last_id)
        
        if mentions and mentions.get("meta", {}).get("result_count", 0) > 0:
            # Tweets are returned oldest first, so iterate normally
            for tweet in mentions["data"]:
                tweet_id = tweet["id"]
                author_id = tweet["author_id"]
                
                # Simple check to avoid replying to itself, though the search query should handle this
                # A more robust check might involve getting the bot's user ID.
                # For now, we rely on the '-from:BOT_USERNAME' in the search query.

                post_reply(tweet_id, REPLY_MESSAGE)
                
                # Update last_id to the newest tweet processed
                last_id = tweet_id

            # Save the ID of the most recent tweet we've replied to
            save_last_tweet_id(last_id)
        else:
            print("No new mentions found.")

        print(f"Waiting for {CHECK_INTERVAL} seconds...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run_bot()
