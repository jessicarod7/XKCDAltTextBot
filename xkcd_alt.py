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
            print("OAuth initiation failed: Environmental variable not found")
            auth = 'crash'
    if key != 'crash':
        auth = OAuth1(key[0], key[1], key[2], key[3])
        print('OAuth initiation successful!')
        del key
        return auth
    else:
        del key
        return auth