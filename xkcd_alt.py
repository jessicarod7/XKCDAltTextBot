"""This is the XKCD Alt Text Bot.

This bot checks once every 15 seconds for new Tweets from a target bot. If one is found, it accesses
the linked image, extracts the image alt text, and Tweets it as a reply."""

import time # Program sleeping
import yaml # API keys, access tokens, and custom logs
import os # Used by Heroku for environmental variable
import math # Round up number of tweets needed
import re # Finds the most recent bot tweet
import requests # Accessing API
from requests_oauthlib import OAuth1 # OAuth
from bs4 import BeautifulSoup # HTML searching

# Global vars
LOG_NAME = None
BOT = None
TARGET = None
WHERE = 0
URL_NUMBER = 0

class Twitter():
    """This class handles all API requests to Twitter."""
    def __init__(self, auth):
        """This class constructor collects the OAuth keys for the class."""
        self.auth = auth
    
    def get(self):
        """This function determines if a new Tweet has been posted, and returns it.
        
        Mentions of 'target' refer to the target Twitter bot, mentions of 'bot' or 'this' refer to this Twitter bot."""
        # Build payloads for source bot and this bot search
        bot_payload = {'q': 'from:{}'.format(BOT), 'result_type': 'recent', 'count': '10'}
        target_payload = {'q': 'from:{}'.format(TARGET), 'result_type': 'recent', 'count': '1'}

        # Retrieve data from Twitter searches
        for attempt in range(6):
            if attempt == 5: # Too many attempts
                print('Twitter search failed ({}), see below response.'.format(str(target_raw.status_code)))
                print('Twitter error message:\n\n{}'.format(target_raw.json()))
                del bot_payload, target_payload
                return 'crash' # Enter log protection mode
            
            print('Searching for new {}s...'.format(LOG_NAME))
            bot_raw = requests.get('https://api.twitter.com/1.1/search/tweets.json',
                                    params=bot_payload, auth=self.auth)
            target_raw = requests.get('https://api.twitter.com/1.1/search/tweets.json',
                                    params=target_payload, auth=self.auth)
            
            if target_raw.status_code == 200: # Good request
                pass
            elif target_raw.status_code >= 429 or target_raw.status_code == 420:
                # Twitter issue or rate limiting
                print('Twitter search failed ({})'.format(target_raw.status_code))
                print('Reattempting in 5 minutes...')
                time.sleep(300) # sleep for 5 minutes and reattempt
                continue
            else: # Other problem in code
                print('Twitter search failed ({}), see below '.format(str(target_raw.status_code)) +
                      'response.')
                print('Twitter error message:\n\n{}'.format(target_raw.json()))
                del bot_payload, target_payload, bot_raw, target_raw
                return 'crash' # Enter log protection mode
            
            # Convert to JSON
            bot_json = bot_raw.json()
            target_json = target_raw.json()

            # Create a list of all reply IDs
            bot_replies = [bot_json['statuses'][i]['in_reply_to_status_id'] for i in
                           range(len(bot_json['statuses']))]

            try:
                if target_json['statuses'][0]['id'] is None:
                    print('Twitter search failed: No Tweet found')
                    del bot_payload, target_payload, bot_raw, target_raw, bot_json, target_json
                    return 'crash' # Enter log protection mode
            except IndexError:
                print('Twitter search failed: No Tweet found')
                del bot_payload, target_payload, bot_raw, target_raw, bot_json, target_json
                return 'crash' # Enter log protection mode

            try:    
                if bot_replies.index(target_json['statuses'][0]['id']) is not ValueError:
                    # This tweet has already been replied to
                    del bot_payload, target_payload, bot_raw, target_raw, bot_json, target_json
                    return None # Sleep for 15 seconds
            except ValueError: # Supposedly valid comment
                return target_json['statuses'][0] # Return target Tweet

    def post(self, tweet, reply):
        """This function Tweets the alt (title) text as a reply to the target account."""
        print('Tweeting...')

        tweet_payload = {'status': tweet, 'in_reply_to_status_id': reply,
                         'auto_populate_reply_metadata': 'true'}
        
        # POST Tweet
        for attempt in range(6):
            if attempt == 5: # Too many attempts
                print('Tweeting failed ({}), see below response.'.format(str(tweet.status_code)))
                print('Twitter error message:\n\n{}'.format(tweet.json()))
                del tweet_payload
                return 'crash' # Enter log protection mode

            tweet = requests.post('https://api.twitter.com/1.1/statuses/update.json',
                                  data=tweet_payload, auth=self.auth)
            
            if tweet.status_code == 200: # Good request
                print('Successfully Tweeted:\n\n{}'.format(tweet.json()))
                del tweet_payload
                return tweet.json()
            elif tweet.status_code >= 429 or tweet.status_code == 420 or \
            tweet.status_code == 403:
                if tweet.json()['errors'][0]['code'] == 187: # Duplicate Tweet
                    print('Duplicate Tweet detected, ending attempt.')
                    return None
                # Twitter issue or rate limiting
                print('Tweeting failed ({})'.format(tweet.status_code))
                print('Reattempting in 5 minutes...')
                time.sleep(300) # sleep for 5 minutes and reattempt
                continue
            else: # Other problem in code
                print('Tweeting failed ({}), see below response.'.format(str(tweet.status_code)))
                print('Twitter error message:\n\n{}'.format(tweet.json()))
                del tweet, tweet_payload
                return 'crash' # Enter log protection mode
    
    def tweetstorm(self, body, num_tweets, orig_tweet):
        """This function posts a chain of tweets if the full Tweet is longer than 280 characters."""
        seek = 0 # Location in body of text

        for n in range(num_tweets): # Post each individual tweet // twit: a short tweet
            if (n+1) < num_tweets:
                endspace = body[seek:seek+280].rfind(' ') # Find the last space under 280 chars
                twit = body[seek:endspace] # Get up to 280 chars of full words
            else: # Final tweet
                twit = body[seek:] # Use the remaining characters
            
            if n is 0:
                result = self.post(twit, orig_tweet) # Reply to the original tweet
            else:
                result = self.post(twit, reply_to) # Reply to the previous tweet
            if result is 'crash':
                return 'crash' # Enter log protection mode
            
            reply_to = result['id_str'] # Tweet for next twit to reply to
            seek += endspace + 1 # Start the next sequence from after the space
        
        return None
        
def get_config():
    """This function retrieves API keys, access tokens, and other key data from the config file."""
    global LOG_NAME, TARGET, URL_NUMBER, WHERE, BOT
    print("Building OAuth header...")

    if 'XKCD_APPNAME' in os.environ: # Running on a cloud server
        key = [os.environ.get('API_KEY', None),
           os.environ.get('API_SECRET_KEY', None),
           os.environ.get('ACCESS_TOKEN', None),
           os.environ.get('ACCESS_TOKEN_SECRET', None)]

        LOG_NAME = os.environ.get('LOG_NAME', None)
        TARGET = os.environ.get('TARGET', None)
        URL_NUMBER = int(os.environ.get('URL_NUMBER', None))
        WHERE = int(os.environ.get('WHERE', None))
        BOT = os.environ.get('BOT', None)

    else: # Running locally
        with open('config.yaml') as config_file:
            CONFIG = yaml.load(config_file)
            key = [CONFIG['API Key'],
                CONFIG['API Secret Key'],
                CONFIG['Access Token'],
                CONFIG['Access Token Secret']]

            LOG_NAME = CONFIG['Target name in logs']
            TARGET = CONFIG['Target account handle']
            URL_NUMBER = int(CONFIG['Tweet URL location'])
            WHERE = int(CONFIG['Target image location on site'])
            BOT = CONFIG['Your account handle']

    for i in key:
        if i is None: # Verify keys were loaded
            print("OAuth initiation failed: API key or access token not found")
            del key
            return 'crash' # Enter log protection mode
    auth = OAuth1(key[0], key[1], key[2], key[3])
    print('OAuth initiation successful!')

    del key
    return auth

def retrieve_text(site):
    """This retrieves the HTML of the website, isolates the image title text, and formats it for the
    Tweet."""
    for attempt in range(11):
        print('Accessing {} (attempt {} of 11)'.format(site, attempt+1))
        html_raw = requests.get(site) # Retrieving raw HTML data
        if html_raw.status_code != 200: # Data not successfully retrieved
            if attempt < 6:
                print('Could not access {} ({}). '.format(LOG_NAME, html_raw.status_code) +
                      'Trying again in 10 seconds...')
                time.sleep(10) # Make 6 attempts with 10 second delays
            elif attempt < 10:
                print('Could not access {} ({}). '.format(LOG_NAME, html_raw.status_code) +
                      'Trying again in 60 seconds...')
                time.sleep(60) # Make 4 attempts with 60 seconds delays
            else:
                print('{} retrieval failed: could not access {}'.format(LOG_NAME, site))
                return 'crash' # Enter log protection mode
        else: # Data retrieved
            break
                
    html = BeautifulSoup(html_raw.text, 'html.parser')
    target_image = html.find_all('img', title=True) # Locates the only image with title text (the target)
    if target_image is None:
        print('Title extraction failed: image not found')
        return 'crash' # Enter log protection mode
    
    title = target_image[WHERE]['title'] # Extracts the title text
    tweet = 'Alt/title text: "{}"'.format(title) # Construct the main Tweet body

    if len(tweet) <= 280: # Char limit
        num_tweets = 1 # The number of tweets that must be created
    else:
        num_tweets = math.ceil(len(tweet) / 280)

    print('Tweet constructed')
    del html_raw, html, target_image, title
    return [tweet, num_tweets]

def crash():
    """This function protects logs by pinging google.com every 20 minutes."""
    print('Entering log protection mode.')
    while True:
        a = requests.get('https://google.com') # Ping Google
        del a
        time.sleep(1200)
        continue

if __name__ == '__main__':
    # All mentions of 'crash' mean the program has crashed, and is entering log protection mode
    auth = get_config() # Build authentication header and get config data
    if auth == 'crash':
        crash()
    twitter = Twitter(auth)

    while True: # Initialize main account loop
        new_tweet_check = None

        for i in range(2):
            original_tweet = twitter.get() # Check for new Tweets

            if original_tweet == 'crash':
                crash()
            elif original_tweet is None:
                print('No new {}s found. Sleeping for 15 seconds...'.format(LOG_NAME))
                time.sleep(15)
                break
            else:
                if new_tweet_check is None: # Unverified new Tweet
                    new_tweet_check = original_tweet
                    print('Potential new {}. Waiting 15 seconds to verify...'.format(LOG_NAME))
                    continue
                elif new_tweet_check == original_tweet: # Confirmed new Tweet
                    [body, num_tweets] = retrieve_text(original_tweet['entities']['urls'][URL_NUMBER]['expanded_url'])
                    if body == 'crash':
                        crash()

                    if num_tweets == 1:
                        result = twitter.post(body, original_tweet['id_str']) # Post one Tweet
                    else:
                        result = twitter.tweetstorm(body, num_tweets, original_tweet['id_str']) # Split into multiple Tweets
                    if result == 'crash':
                                crash()
                    else: # Successful Tweet
                        del result
                        print('Sleeping for 60 seconds...')
                        time.sleep(60)
                        break
                else:
                    print('Twitter search returned existing {}. Sleeping for 15 seconds...'.format(LOG_NAME))
                    break