"""This is the XKCD Alt Text Bot.

This bot checks once every 15 seconds for new Tweets from @xkcdComic. If one is found, it accesses the
linked comic, extracts the image alt text, and Tweets it as a reply."""

import time # Program sleeping
import os # API keys & access tokens
import math # Round up number of tweets needed
import re # Finds the most recent bot tweet
import requests # Accessing API
from requests_oauthlib import OAuth1 # OAuth
from bs4 import BeautifulSoup # HTML searching

class Twitter():
    """This class handles all API requests to Twitter."""
    def __init__(self, auth):
        """This class constructor collects the OAuth keys for the class."""
        self.auth = auth
    
    def get(self):
        """This function determines if a new comic has been posted, and returns it.
        
        Mentions of 'comic' refer to @xkcdComic, mentions of 'alt' refer to @XKCDAltTextBot."""
        # Build payloads for comic bot and alt text bot search
        alt_payload = {'q': 'from:XKCDAltTextBot', 'result_type': 'recent', 'count': '10'}
        comic_payload = {'q': 'from:xkcdComic', 'result_type': 'recent', 'count': '1'}

        # Retrieve data from Twitter searches
        for attempt in range(6):
            if attempt == 5: # Too many attempts
                print('Twitter search failed ({}), see below response.'.format(str(comic_raw.status_code)))
                print('Twitter error message:\n\n{}'.format(comic_raw.json()))
                del alt_payload, comic_payload
                return 'crash' # Enter log protection mode
            
            print('Searching for new comics...')
            alt_raw = requests.get('https://api.twitter.com/1.1/search/tweets.json',
                                    params=alt_payload, auth=self.auth)
            comic_raw = requests.get('https://api.twitter.com/1.1/search/tweets.json',
                                    params=comic_payload, auth=self.auth)
            
            if comic_raw.status_code == 200: # Good request
                pass
            elif comic_raw.status_code >= 429 or comic_raw.status_code == 420:
                # Twitter issue or rate limiting
                print('Twitter search failed ({})'.format(comic_raw.status_code))
                print('Reattempting in 5 minutes...')
                time.sleep(300) # sleep for 5 minutes and reattempt
                continue
            else: # Other problem in code
                print('Twitter search failed ({}), see below '.format(str(comic_raw.status_code)) +
                      'response.')
                print('Twitter error message:\n\n{}'.format(comic_raw.json()))
                del alt_payload, comic_payload, alt_raw, comic_raw
                return 'crash' # Enter log protection mode
            
            # Convert to JSON
            alt = alt_raw.json()
            comic = comic_raw.json()

            # Create a list of all reply IDs
            alt_replies = [alt['statuses'][i]['in_reply_to_status_id'] for i in
                           range(len(alt['statuses']))]

            try:
                if comic['statuses'][0]['id'] is None:
                    print('Twitter search failed: No Tweet found')
                    del alt_payload, comic_payload, alt_raw, comic_raw, alt, comic
                    return 'crash' # Enter log protection mode
            except IndexError:
                print('Twitter search failed: No Tweet found')
                del alt_payload, comic_payload, alt_raw, comic_raw, alt, comic
                return 'crash' # Enter log protection mode

            try:    
                if alt_replies.index(comic['statuses'][0]['id']) is not ValueError:
                    # This tweet has already been replied to
                    del alt_payload, comic_payload, alt_raw, comic_raw, alt, comic
                    return None # Sleep for 15 seconds
            except ValueError: # Supposedly valid comment
                return comic['statuses'][0] # Return comic Tweet

    def post(self, tweet, reply):
        """This function Tweets the alt (title) text as a reply to @xkcdComic."""
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
        
def get_auth():
    """This function retrieves the API keys and access tokens from environmental variables."""
    print("Building OAuth header...")
    key = [os.environ.get('XKCD_API_KEY', None),
           os.environ.get('XKCD_API_SECRET_KEY', None),
           os.environ.get('XKCD_ACCESS_TOKEN', None),
           os.environ.get('XKCD_ACCESS_SECRET_TOKEN', None)]
    for i in key:
        if i is None: # Verify keys were loaded
            print("OAuth initiation failed: Environmental variable not found")
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
                print('Could not access XKCD ({}). '.format(html_raw.status_code) +
                      'Trying again in 10 seconds...')
                time.sleep(10) # Make 6 attempts with 10 second delays
            elif attempt < 10:
                print('Could not access XKCD ({}). '.format(html_raw.status_code) +
                      'Trying again in 60 seconds...')
                time.sleep(60) # Make 4 attempts with 60 seconds delays
            else:
                print('XKCD retrieval failed: could not access {}'.format(site))
                return 'crash' # Enter log protection mode
        else: # Data retrieved
            break
                
    html = BeautifulSoup(html_raw.text, 'html.parser')
    comic = html.find('img', title=True) # Locates the only image with title text (the comic)
    if comic is None:
        print('Title extraction failed: image not found')
        return 'crash' # Enter log protection mode
    
    title = comic['title'] # Extracts the title text
    tweet = 'Alt/title text: "{}"'.format(title) # Construct the main Tweet body

    if len(tweet) <= 280: # Char limit
        num_tweets = 1 # The number of tweets that must be created
    else:
        num_tweets = math.ceil(len(tweet) / 280)

    print('Tweet constructed')
    del html_raw, html, comic, title
    return [tweet, num_tweets]

def crash():
    """This function protects logs by pinging google.com every 20 minutes."""
    print('Entering log protection mode.')
    while True:
        a = requests.get('https://google.com') # Ping Google
        del a
        time.sleep(1200)
        continue

# Main program
# All mentions of 'crash' mean the program has, and is entering log protection mode
auth = get_auth() # Build authentication header
if auth == 'crash':
    crash()
twitter = Twitter(auth)

while True: # Initialize main account loop
    original_tweet = twitter.get() # Check for new comics

    if original_tweet == 'crash':
        crash()
    elif original_tweet is None:
        print('No new comics found. Sleeping for 15 seconds...')
        time.sleep(15)
        continue
    else: # Retrieve text
        [body, num_tweets] = retrieve_text(original_tweet['entities']['urls'][0]['expanded_url'])
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
            continue