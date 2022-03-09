"""This is the XKCD Alt Text Bot.

This bot checks once every 15 seconds for new Tweets from a target bot. If one is found, it accesses
the linked image, extracts the image alt text, and Tweets it as a reply."""

import time # Program sleeping
import datetime # Cancels Tweet if older than 6 hours
import calendar # Converts calendar abbreviation to integer
from dateutil.tz import gettz # Switches to UTC in recent Tweet check
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
        # Build payloads for source bot and this bot retrieval
        bot_payload = {'screen_name': '{}'.format(BOT), 'count': '10'}
        target_payload = {'screen_name': '{}'.format(TARGET), 'count': '1'}

        # Retrieve data from Twitter retrievals
        for attempt in range(6):
            if attempt == 5: # Too many attempts
                print('Twitter retrieval failed ({}), see below response.'.format(str(target_raw.status_code)))
                print('Twitter error message:\n\n{}'.format(target_raw.json()))
                del bot_payload, target_payload
                return 'crash' # Enter log protection mode
            
            print('Retrieving new {}s...'.format(LOG_NAME))
            bot_raw = requests.get('https://api.twitter.com/1.1/statuses/user_timeline.json',
                                    params=bot_payload, auth=self.auth)
            target_raw = requests.get('https://api.twitter.com/1.1/statuses/user_timeline.json',
                                    params=target_payload, auth=self.auth)
            
            if target_raw.status_code == 200: # Good request
                pass
            elif target_raw.status_code >= 429 or target_raw.status_code == 420:
                # Twitter issue or rate limiting
                print('Twitter retrival failed ({})'.format(target_raw.status_code))
                print('Reattempting in 5 minutes...')
                time.sleep(300) # sleep for 5 minutes and reattempt
                continue
            else: # Other problem in code
                print('Twitter retrieval failed ({}), see below '.format(str(target_raw.status_code)) +
                      'response.')
                print('Twitter error message:\n\n{}'.format(target_raw.json()))
                del bot_payload, target_payload, bot_raw, target_raw
                return 'crash' # Enter log protection mode
            
            # Convert to JSON
            bot_json = bot_raw.json()
            target_json = target_raw.json()

            # Create a list of all reply IDs
            bot_replies = [bot_json[i]['in_reply_to_status_id'] for i in
                           range(len(bot_json))]

            try:
                if target_json[0]['id'] is None:
                    print('Twitter retrieval failed: No Tweet found')
                    del bot_payload, target_payload, bot_raw, target_raw, bot_json, target_json
                    return 'crash' # Enter log protection mode
            except IndexError:
                print('Twitter retrieval failed: No Tweet found')
                del bot_payload, target_payload, bot_raw, target_raw, bot_json, target_json
                return 'crash' # Enter log protection mode

            for i in range(len(bot_replies)):
                if bot_replies[i] == target_json[0]['id']:
                    try:
                        if bot_json[i]['retweeted_status'] is not None:
                            continue # Retweet, keep going
                    except KeyError:
                        return None # Already replied, sleep for 15 seconds
            
            # Do not reply to tweets older than 6 hours
            tweet_time_str = datetime.datetime(
                int(target_json[0]['created_at'][-4:]),
                list(calendar.month_abbr).index(target_json[0]['created_at'][4:7]),
                int(target_json[0]['created_at'][8:10]),
                int(target_json[0]['created_at'][11:13]),
                int(target_json[0]['created_at'][14:16]),
                int(target_json[0]['created_at'][17:19]),
                0,
                gettz('UTC')
            )
            tweet_time = time.mktime(tweet_time_str.timetuple())

            del bot_payload, target_payload, bot_raw, target_raw, bot_json
            if time.mktime(datetime.datetime.utcnow().timetuple()) - tweet_time > 21600:
                del target_json
                return None # Tweet is too old
            else:
                return target_json[0] # Return target Tweet

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
            
            if n == 0:
                result = self.post(twit, orig_tweet) # Reply to the original tweet
            else:
                result = self.post(twit, reply_to) # Reply to the previous tweet
            if result == 'crash':
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
            CONFIG = yaml.safe_load(config_file)
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
    for attempt in range(101):
        print('Accessing {} (attempt {} of 100)'.format(site, attempt+1))
        # Add user agent to minimize 404 errors
        ua_header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'}
        html_raw = requests.get(site, headers=ua_header) # Retrieving raw HTML data
        if html_raw.status_code != 200: # Data not successfully retrieved
            if attempt < 60:
                print('Could not access {} ({}). '.format(LOG_NAME, html_raw.status_code) +
                      'Trying again in 5 seconds...')
                time.sleep(5) # 5 minutes of attempts
            elif attempt < 90:
                print('Could not access {} ({}). '.format(LOG_NAME, html_raw.status_code) +
                      'Trying again in 10 seconds...')
                time.sleep(10) # Another 5 minutes of attempts
            elif attempt < 100:
                print('Could not access {} ({}). '.format(LOG_NAME, html_raw.status_code) +
                      'Trying again in 30 seconds...')
                time.sleep(30) # Last 5 minutes of attempts
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
    tweet_title = 'Title text: "{}"'.format(title) 
    
    # This block acts as a Tweet 'header'
    tweet_header_size = 36 # URL is 23 chars
    tweet_header = 'Alt text @ https://www.explainxkcd.com/wiki/index.php/{}#Transcript'.format(site[-5:-1]) + '\n\n'
    tweet = tweet_header + tweet_title

    if (len(tweet_title) + tweet_header_size) <= 280: # Char limit, incl. link
        num_tweets = 1 # The number of tweets that must be created
    else:
        num_tweets = math.ceil((len(tweet_title) + tweet_header_size) / 280)

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
    new_tweet_check = [0, None]
    if auth == 'crash':
        crash()
    twitter = Twitter(auth)

    while True: # Initialize main account loop
        if new_tweet_check[0] > 3: # Too many attempts
            print('Verification failed.')
            new_tweet_check = [0, None]
            continue
        else:
            original_tweet = twitter.get() # Check for new Tweets

        if original_tweet == 'crash':
            new_tweet_check = [0, None]
            crash()
        elif original_tweet is None:
            print('No new {}s found. Sleeping for 15 seconds...'.format(LOG_NAME))
            if new_tweet_check[0] > 0:
                new_tweet_check[0] += 1
            time.sleep(15)
        else:
            if new_tweet_check[1] is None: # Unverified new Tweet
                new_tweet_check[1] = original_tweet['id']
                print('Potential new {}. Waiting 5 seconds to verify...'.format(LOG_NAME))
                time.sleep(5)
            elif new_tweet_check[1] == original_tweet['id']: # Confirmed new Tweet
                [body, num_tweets] = retrieve_text(original_tweet['entities']['urls'][URL_NUMBER]['expanded_url'])
                if body == 'crash':
                    new_tweet_check = [0, None]
                    crash()

                if num_tweets == 1:
                    result = twitter.post(body, original_tweet['id_str']) # Post one Tweet
                else:
                    result = twitter.tweetstorm(body, num_tweets, original_tweet['id_str']) # Split into multiple Tweets
                if result == 'crash':
                    new_tweet_check = [0, None]
                    crash()
                else: # Successful Tweet
                    del result
                    print('Sleeping for 60 seconds...')
                    time.sleep(60)
                    new_tweet_check = [0, None]
            else:
                print('Twitter retrieval returned existing {}. Sleeping for 5 seconds...'.format(LOG_NAME))
                new_tweet_check[0] += 1
                time.sleep(5)