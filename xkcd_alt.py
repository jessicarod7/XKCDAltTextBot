"""This is the XKCD Alt Text Bot.

This bot checks once a minute for new Tweets from @xkcdComic. If one is found, it accesses the
linked comic, extracts the image alt text, and Tweets it as a reply."""

import time # Program sleeping
import os # API keys & access tokens
import requests # Accessing API
from requests_oauthlib import OAuth1 # OAuth
from bs4 import BeautifulSoup # HTML searching

class Twitter():
    """This class handles all API requests to Twitter."""
    def __init__(self, auth):
        """This class constructor collects the OAuth keys for the class."""
        self.auth = auth
    
    def get(self):
        """This function returns the result of the Twitter search for the reply to @xkcdComic."""
        pass

    def post(self, tweet):
        """This function Tweets the alt (title) text as a reply to @xkcdComic."""
        pass

def get_auth():
    """This function retrieves the API keys and access tokens from environmental variables."""
    key = [os.environ.get('XKCD_API_KEY', None),
           os.environ.get('XKCD_API_SECRET_KEY', None),
           os.environ.get('XKCD_ACCESS_TOKEN', None),
           os.environ.get('XKCD_ACCESS_SECRET_TOKEN', None)]
    for i in key:
        if i is None: # Verify keys were loaded
            print("OAuth initiation failed: Environmental variable {} not found".format(i+1))
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
        print('Accessing {} (attempt {} of 11'.format(site, attempt+1))
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
                
    html = BeautifulSoup(html_raw, 'html.parser')
    comic = html.find('img', title=True) # Locates the only image with title text (the comic)
    if comic is None:
        print('Title extraction failed: image not found')
        return 'crash' # Enter log protection mode
    
    title = comic['title'] # Extracts the title text
    tweet = 'Alt/title text: "{}"'.format(title) # Construct the main Tweet body

    print('Tweet constructed')
    del html_raw, html, comic, title
    return tweet