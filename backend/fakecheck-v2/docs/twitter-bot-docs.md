
Tutorial

How to create an X bot with v2 of the X API
X API
X Bot
How to create an X bot with v2 of the X API
X Developer Staff

We recently launched new manage Tweets endpoints. Creating Posts using the X API is essential for engaging with the public conversation. X bots are an integral part of the conversation on X. Some bots show old roadside pictures, bots that watch TV, and even check a flood forecast.

@FactualCat is an X Bot that posts Cat facts daily that was built as an example to help you build X bots. This bot parses cat facts from an API that provides cat facts, catfact.ninja and posts them out. This bot uses the manage Tweets endpoint in the X API v2 deployed with Google Cloud Functions and Cloud Scheduler. In this tutorial, you’ll learn how this example was built and deployed.

Endpoints

Manage Tweets →
Resources

Google Cloud Platform (GCP) →

When writing this tutorial, the cost of hosting this Twitter bot should be covered by the free credits from the Google Cloud Platform. If this changes, please let us know by selecting the unhappy face at the bottom of the page.

Create your bot account
First, you will need to create a new account for your bot. The account for your bot should be a unique handle that describes your bot’s purpose. You will also want to set your bot’s profile picture and background image. Additionally, you will want to set up the bio of your bot to say it’s a bot and who built it. 

For @FactualCat, the bio is as follows: 

A #TwitterBot that Tweets cat facts by @JessicaGarson

 

Authenticate on behalf of your bot
Before you can use the Twitter API v2, you will need a developer account. Once you have a developer account, you will need to create a Project in the developer portal. This tutorial uses v1.1 endpoints. To use v1.1 endpoints, you will need elevated access, which you can apply for from the developer portal.

Each Project contains an App, with which you can generate the credentials required to use the Twitter API. You can learn more about getting started with the Twitter API in the getting started section of our documentation. You can apply for access from your main handle and authenticate on behalf of your account.

To authenticate a new account, you can use a pin-based OAuth flow. A helpful forum post also explains how to authenticate on behalf of a bot account.

Step 1 - Get your OAuth token
You can use a REST Client such as Insomnia or Postman to make a POST request to the request token endpoint. For this endpoint, you will need to use OAuth 1.0a. 

https://api.x.com/oauth/request_token

After you make the request you will get back a response that looks similar to the one below:

 

oauth_token=zlgW3QAAAAAA2_NZAAABfxxxxxxk&oauth_token_secret=pBYEQzdbyMqIcyDzyn0X7LDxxxxxxxxx&oauth_callback_confirmed=true
Step 2 - Create and go to the authenticate URL 
Using the OAuth token you generated in the last step, you can create a URL that you can go to authorize your application. You should be signed in as your bot account when you visit this URL. You will start with the prefix of https://api.x.com/oauth/authenticate?oauth_token= and append it with the OAuth token from the previous step.

For this example, the URL you’d visit in your web browser would be similar to the one below but replaced with the credentials generated from the previous step. Authorizing on a browser will return a seven-digit pin as an OAuth verifier in the next step.

https://api.x.com/oauth/authenticate?oauth_token=zlgW3QAAAAAA2_NZAAABfxxxxxxk

You can learn more about creating an authenticate URL in our documentation on the subject.

Step 3 - Getting your Access Token and Access Token Secret
You are now ready to get the Access Token and Access Token Secret for your bot account. Next, you will use the POST oauth/access_token endpoint. For this endpoint, you will need to use OAuth 1.0a. 

You can now make a POST request to the following endpoint using the OAuth verifier you generated in the previous step and the OAuth token you used in the last step. 

https://api.x.com/oauth/access_token?oauth_verifier=0535121&oauth_token=zlgW3QAAAAAA2_NZAAABfxxxxxxk

You should get back to a response that is similar to the following: 

oauth_token=62532xx-eWudHldSbIaelX7swmsiHImEL4KinwaGloxxxxxx&oauth_token_secret=2EEfA6BG5ly3sR3XjE0IBSnlQu4ZrUzPiYxxxxxx&user_id=1458900662935343104&screen_name=FactualCat
The oauth_token you get back is the Access Token for your bot, and the oauth_token_secret is the Access Token Secret for your bot.

 

Posting your first Tweet on behalf of your bot
Now that you’ve created your Access Token and Access Token Secret, you are now ready to start Tweeting on behalf of your bot. Like how you used OAuth 1.0 in a REST Client such as Insomnia or Postman in the previous steps, you can now do the same but be sure to replace the Access Token and Access Token Secret with the ones you just created. The Consumer Key and Consumer Secret should be the same as they were previously. 

You can now make a POST request to the manage Tweets endpoint by entering the following URL into Insomnia or Postman: 

https://api.x.com/2/tweets

In the body tab of your request, be sure to select the format as JSON and enter in the following payload: 

{"text": "hello"}
The response should look similar to the following:

{
  "data": {
    "id": "1464995641172582404",
    "text": "hello"
  }
}
If you check your bot account, you will see that you have posted your first Tweet on behalf of your bot. 

 

Setting up Google Cloud Functions
Now that you’ve posted your first Tweet on behalf of your bot, you are ready to start configuring your bot to run regularly. First, you will deploy and write your code in Google Cloud Functions and run it at a scheduled time that you determine with Google Cloud Scheduler. 

You will first need to set up an environment for the Google Cloud Platform. After you have your environment set up, you can set up a Cloud Function. If you are using Google Cloud Platform for the first time, you will need to set up a credit card before creating an environment. To set up a Cloud Function, you can follow a similar process outlined in the Python quickstart for Cloud Functions. You can first set your cloud region based on your location and select your trigger as “Cloud Pub/Sub” with a new topic.

Creating your environment variables
To avoid directly adding your keys and tokens to your Cloud Function, you can create environment variables. For example, under the “Runtime, build, connections and security settings“ header, you can set up environment variables for your Consumer Key, Consumer Secret, Access Token, and Access Token Secret. Of course, you will want to set these values the same as what you used while posting the Tweet in the previous step. 

Configuring your code
After configuring your Cloud Function, you will be taken to a code page to set your runtime, the programming language, and the version you are using. This example uses Python 3.9 as the runtime environment. You will also want to select the entry point as hello_pubsub.

Editing your main.py file
The main.py file is where the main logic of the code lives. In this file, you will be parsing a cat fact for this bot from catfact.ninja and Tweeting it from the Twitter API. 

First, you will need to import the following packages.

import requests
from requests_oauthlib import OAuth1
import os
After you’ve imported your packages, you will want to write a few lines of code to get the environment variables you set while configuring your Cloud Function.

consumer_key = os.environ.get("CONSUMER_KEY")
consumer_secret = os.environ.get("CONSUMER_SECRET")
access_token = os.environ.get("ACCESS_TOKEN")
access_token_secret = os.environ.get("ACCESS_TOKEN_SECRET")
After you have the keys and tokens set for your Cloud Function, you can now call the catfact.ninja endpoint to grab a random cat fact.

def random_fact():
    fact = requests.get("https://catfact.ninja/fact?max_length=280").json()
    return fact["fact"]
You will also need to place the cat fact into a dictionary so that you can pass it as a JSON payload.

def format_fact(fact):
   return {"text": "{}".format(fact)}
To make the request to the Twitter API, you can use the following function:

def connect_to_oauth(consumer_key, consumer_secret, acccess_token, access_token_secret):
   url = "https://api.x.com/2/tweets"
   auth = OAuth1(consumer_key, consumer_secret, acccess_token, access_token_secret)
   return url, auth
Now, you are ready to edit the hello_pubsub function to have variables for your fact, payload, url, auth, and request.

def hello_pubsub(event, context):
   fact = random_fact()
   payload = format_fact(fact)
   url, auth = connect_to_oauth(
       consumer_key, consumer_secret, access_token, access_token_secret
   )
   request = requests.post(
       auth=auth, url=url, json=payload, headers={"Content-Type": "application/json"}
   )
You can check out the full version of the code. There is also a version available for testing locally on your machine. You will need to set up the environment variables for the local version to work. 

Editing your requirements.txt file
Your requirements.txt file determines what packages you need to install and installs them in your environment for you.

If you go to the requirements.txt file, you will want to edit it to match the following:

# Function dependencies, for example:
# package>=version

requests==2.18.3
requests-oauthlib==1.3.0
Deploying your function
Once you have your code set, you are now ready to press the button that says “Deploy” to deploy your function. You may want to check out the pricing structure for Cloud Functions.  

 

Scheduling your Tweets with Google Cloud Scheduler 
After setting up your Cloud Function, you can use the Cloud Scheduler to determine how often your bot will Tweet. You need to set up a job and how often it will run. 

For example, @FactualCat is currently Tweeting every 12 hours using the following notation:

0 */12 * * *
You may want to look at the pricing information on the Cloud Scheduler before adjusting the timing.

Creating a Twitter bot with Python, OAuth 2.0, and v2 of the Twitter API
By Jessica Garson

Bots on Twitter are what make the conversation on Twitter so lively. There are many unique bots on Twitter, such as tiny aquariums warning you of sewer overflow in NYC. Bots make Twitter unique and engaging. 

When our team launched the manage Tweets endpoints, I built a bot @FactualCat that Tweeted cat facts daily. This bot used OAuth 1.0a to authenticate, but I wanted to challenge myself to create a bot that used OAuth 2.0 Authorization Code Flow with PKCE. 

Since I was used to the OAuth 1.0a authentication flow, I had a hard time figuring out exactly what I needed to do to authenticate on behalf of my bot and get it running so that it could make requests regularly.  

This tutorial will walk you through the method I used to make @Factual__Dog, a bot that Tweets dog facts twice daily. By the end of this tutorial, you should be able to create a Twitter bot that utilizes OAuth 2.0 Authorization Code Flow with PKCE for authentication. 

The complete code for this tutorial can be found on our GitHub.

Endpoints

Manage Tweets →
OAuth 2.0 Authorization Code Flow with PKCE →
Resources

Render →

Prerequisites
 

A developer account. If you don’t already have access to the Twitter API, you can sign up for a developer account
A Project in the developer portal
An App containing the credentials required to use the Twitter API
OAuth 2.0 turned on in your App’s authentication settings
An account with Render set up to use Redis and Cron Jobs
 

In our platform overview, you can learn more about getting started with the Twitter API.

 

How do bots work with OAuth 2.0? 
With OAuth 2.0, your access token, the credential you use to request v2 endpoints, stays valid for two hours. Since bots run automatically, it’s important to figure out how to handle refreshing tokens and save them to a database. While refresh tokens remain valid for six months to allow flexibility to change the timing, it might be best to generate a new one each time the bot posts a Tweet. 

Since Redis is a key-value store, it seemed to be an excellent place to store my refresh tokens. Since this bot only Tweets on behalf of @Factual__Dog, there is only one entry in the Redis database that gets saved over each time. You could use this same database to save tokens for other bots if needed. 

In this tutorial, your bot account will need to log into Twitter to authenticate your App on behalf of your new bot. When the bot account logs in for the first time, it can post its first Tweet and add a token to the database. To do this, you will create a Flask application that you can run locally. 

After that, you can create a script that will run regularly using a cron job. This script will obtain your most recent OAuth 2.0 tokens from your Redis queue and refresh your tokens. This is because your access token, your primary access credential for using OAuth 2.0, will only stay valid for two hours. Finally, it will post a new Tweet and save your latest set of tokens to a Redis instance.

 

Step 1
Setting up your bot
First, you need to create a new account for your bot. Your account should be a unique handle describing your bot’s purpose. You will also set up the bio of your bot to say it’s a bot. 

You can also now add a label to your account so everyone knows that your account is an automated bot. To attach a label to your bot account, follow these steps:

Go to your account settings 
Select “Your account”
Select “Your account information”
Select “Automation”
Select “Managing account”
Next, select the Twitter account, which runs your bot account
Enter your password to log in
Finally, you should see confirmation that the label has been applied to your account
Step 2

Start Tweeting on behalf of your bot
Before starting to create your bot, let's try out the functionality first. First, you can visit this site and authorize our demo App to Tweet a dog fact if you are logged in to your bot’s Twitter account. Later in step 4, you will build a version of this site that you can run locally to set up your database and Tweet the first Tweet on your bot’s behalf. 

To continue experimenting with making calls to the Twitter API, check out the Twitter API Playground.

Step 3

Setting up a database
Since you’ll have to save the tokens you created via the OAuth 2.0 flow, setting up a database is essential for having an up-to-date access token each time your bot account posts a new Tweet. For this database, you can use Render’s Redis database. You will want to review their pricing information before getting started. To set up Redis, follow the steps outlined in Render’s getting started documentation for setting up Redis.

Additionally, you will need to set up the ability to connect to Redis from outside of Render. You will want to create an environment variable to ensure you are not directly saving your database connection. Using an environment will also make your code more flexible since you will use an internal link when you deploy your application. 

You can set your environment variable in your terminal. You will want to replace where it says link_you_copied_from_your_external_connection_string with your external variable that will look something like this rediss://username:password@host:port

 

export REDIS_URL=’link_you_copied_from_your_external_connection_string’
Step 4

Creating a Flask application to Tweet the first Tweet
Now that you have set the database, we can now create an application to authenticate on behalf of our bot account and save our tokens. 

Installing the required packages
To download all the packages you need, you will want to run the following command in your terminal:

pip install requests redis requests_oauthlib flask
You will be using requests to make HTTP requests to the Twitter API, redis to store your keys and tokens, requests_oauthlib to use OAuth 2.0, and flask to create the web framework so we can easily have our account authenticated.

Creating your main.py file
Now that you have all the required packages installed, you can make the directory and files needed in your terminal by entering the following commands.

mkdir dog-fact-twitter-bot
cd dog-fact-twitter-bot
touch main.py
In your code editor, you can open up your main.py and start editing it. At the top of the file, you can import all the required packages.

import base64
import hashlib
import os
import re
import json
import requests
import redis
from requests.auth import AuthBase, HTTPBasicAuth
from requests_oauthlib import OAuth2Session, TokenUpdated
from flask import Flask, request, redirect, session, url_for, render_template
Since you will be using Redis as your database, you will need to get the environment variable from the previous step and save it into a variable named r that can be called whenever we need to access the database. Using an environment variable allows us to be flexible because you will use an internal connection string when you deploy your bot.

r = redis.from_url(os.environ["REDIS_URL_DOGS"])
You will need to set a variable for your app to initialize it, as is typical at the start of every Flask app. You can also create a secret key for your app, so it’s a random string using the os package.

app = Flask(__name__)
app.secret_key = os.urandom(50)
Now, you are ready to set up your code to authenticate on behalf of another user. To do this, you will want to go into the authentication settings of your App in the developer portal and turn on OAuth 2.0 for authentication. I am currently using the type of App as a public client, a single-page App. After you complete this step, your OAuth 2.0 client ID and secret will show at the bottom of your App’s keys and tokens. 

You will also want to add a new redirect URI. It’s also referred to as a callback URL. This is for testing this bot locally:

http://127.0.0.1:5000/oauth/callback

To keep our code secure and flexible, you can set up environment variables in your terminal.

 

export CLIENT_ID=’xxxxxxxxxxxxxx’
export CLIENT_SECRET=’xxxxxxxxxxx’
export REDIRECT_URI=’http://127.0.0.1:5000/oauth/callback’
Back in your Python file, you can set up variables to get your environment variables for your client_id and client_secret. Additionally, you’ll need to define variables for the authorization URL as auth_url and the URL for obtaining your OAuth 2.0 token as token_url. You will also want to get the environment variable you set for your redirect URI and pass that into a new variable called redirect_uri.

client_id = os.environ.get("CLIENT_ID")
client_secret = os.environ.get("CLIENT_SECRET")
auth_url = "https://twitter.com/i/oauth2/authorize"
token_url = "https://api.x.com/2/oauth2/token"
redirect_uri = os.environ.get("REDIRECT_URI")
Now we can set the permissions you need for your bot by defining scopes. You can use the authentication mapping guide to determine what scopes you need based on your endpoints. 

The scopes for this demo are tweet.read, users.read, tweet.write and offline_access. 

tweet.read allows you to read Tweets 
users.read allows you to obtain information about users
tweet.write allows you to create Tweets
offline.access allows you to generate a refresh token to stay connected to a Twitter account longer than two hours.
scopes = ["tweet.read", "users.read", "tweet.write", "offline.access"]
Since Twitter’s implementation of OAuth 2.0 is PKCE-compliant, you will need to set a code verifier. This is a secure random string. This code verifier is also used to create the code challenge.

code_verifier = base64.urlsafe_b64encode(os.urandom(30)).decode("utf-8")
code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)
In addition to a code verifier, you will also need to pass a code challenge. The code challenge is a base64 encoded string of the SHA256 hash of the code verifier.

code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
code_challenge = code_challenge.replace("=", "")
To connect to manage Tweets endpoint, you’ll need an access token. To create this access token, you can create a function called make_token which will pass in the needed parameters and return a token.

def make_token():
    return OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scopes)
Since your bot will Tweet random facts about dogs, you will need to get these from somewhere. There is a dog fact API that you can call to get facts to Tweet. The function parse_dog_fact allows you to make a GET request to the dog fact endpoint and format the JSON response to get a fact you can later Tweet.

def parse_dog_fact():
    url = "http://dog-api.kinduff.com/api/facts"
    dog_fact = requests.request("GET", url).json()
    return dog_fact["facts"][0]
To Tweet the dog fact, you can make a function that will indicate it is Tweeting which helps debug and makes a POST request to the Manage Tweets endpoint.

def post_tweet(payload, token):
    print("Tweeting!")
    return requests.request(
        "POST",
        "https://api.x.com/2/tweets",
        json=payload,
        headers={
            "Authorization": "Bearer {}".format(token["access_token"]),
            "Content-Type": "application/json",
        },
    )
At this point, you’ll want to set up the landing page for your bot to authenticate. Your bot will log into a page that lists the permissions needed.

@app.route("/")
def demo():
    global twitter
    twitter = make_token()
    authorization_url, state = twitter.authorization_url(
        auth_url, code_challenge=code_challenge, code_challenge_method="S256"
    )
    session["oauth_state"] = state
    return redirect(authorization_url)
After the account gives permission to your App you can get the access token. You can format your token to save it as a JSON object into a Redis key/value store so that you can refresh the token the next time your bot Tweets. 

After you save the token, you can parse the dog fact using the function parse_dog_fact. You will also need to format the doggie_fact  into a JSON object. After, you can pass the payload in as a payload into your post_tweet.

@app.route("/oauth/callback", methods=["GET"])
def callback():
    code = request.args.get("code")
    token = twitter.fetch_token(
        token_url=token_url,
        client_secret=client_secret,
        code_verifier=code_verifier,
        code=code,
    )
    st_token = '"{}"'.format(token)
    j_token = json.loads(st_token)
    r.set("token", j_token)
    doggie_fact = parse_dog_fact()
    payload = {"text": "{}".format(doggie_fact)}
    response = post_tweet(payload, token).json()
    return response


if __name__ == "__main__":
    app.run()
To run the file locally, run the following line in your terminal:

python main.py
If you have successfully Tweet you should see a JSON payload in your browser that looks similar to this one: 

{"data":{"id":"1570212002706104320","text":"A lost Dachshund was found swallowed whole in the stomach of a giant catfish in Berlin on July 2003."}}
Step 5

Automate your bot’s Tweets
Every other Tweet after the first
Now that you’ve created a framework for a bot account to log into and set your first token. You can now set up a script that regularly Tweets on your account's behalf. 

In your terminal, you can create a new file.

touch every_other_dogs.py
In your code editor, you will now want to import the packages you need. Your first import will be the main.py you created in the last step. You will also want to import redis for obtaining and saving your access token objects, json for formatting tokens into JSON objects, and os for working with environment variables.

import main
import redis
import json
import os
You can now set a variable called twitter, which calls the make_token function to create a new access token. You will also need to obtain the environment variables for client ID and client secret. 

twitter = main.make_token()
client_id = os.environ.get("CLIENT_ID")
client_secret = os.environ.get("CLIENT_SECRET")
token_url = "https://api.x.com/2/oauth2/token"
Now, you can obtain the access token from Redis, which is saved corresponding with the value of token. You will also need to decode the token and replace the quotes. You can save it into a JSON object and work with it later.

t = main.r.get("token")
bb_t = t.decode("utf8").replace("'", '"')
data = json.loads(bb_t)
Since access tokens in OAuth 2.0 only stay valid for two hours, you will need to refresh your token. Refresh tokens typically stay valid for about six months.

refreshed_token = twitter.refresh_token(
    client_id=client_id,
    client_secret=client_secret,
    token_url=token_url,
    refresh_token=data["refresh_token"],
)
To save the token, you will need to ensure it has the proper quotations around it and load into a JSON object before you can save it back into Redis with the value of token.

st_refreshed_token = '"{}"'.format(refreshed_token)
j_refreshed_token = json.loads(st_refreshed_token)
main.r.set("token", j_refreshed_token)
After saving the newly refreshed token back into Redis, now you can obtain a new dog fact from the dog fact API, pass that into a JSON payload, and Tweet.

doggie_fact = main.parse_dog_fact()
payload = {"text": "{}".format(doggie_fact)}
main.post_tweet(payload, refreshed_token)
If you want to run this script locally to test it out, use the following command:

python every_other_dogs.py
Deployment
For this bot to run automatically, you will want to deploy it to a server.  Currently, this bot is deployed using Render. I used a similar method to their documentation on flask deployment. I have also set up a cron job that runs the every_other_dogs.py file every 12 hours using the following notion: 

0 */12 * * *

To serve the correct URI redirect, I had to deploy the application first to figure out my URL and set it up in my environment variables in Render and the developer portal.

The redirect URI for my application was as follows:

https://factual-dog.onrender.com/oauth/callback

Additionally, you will need to set up environment variables for Client ID and Client Secret in your environment variable in your settings in Render. You also will have to set up an environment variable for your internal Redis connection string, which is different from the one you used for testing.

