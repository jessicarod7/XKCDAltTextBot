"""This program will setup your environment variables for Heroku."""

import subprocess # Runs commands
import yaml

if __name__ == '__main__':
    cmd = 'heroku config:set'

    with open('config.yaml') as config_file:
        CONFIG = yaml.load(config_file)
        appname = '--app {}'.format(CONFIG['Heroku bot name'])
        # Push all config vars to Heroku environment vars
        temp = subprocess.call('{} API_KEY={} {}'.format(cmd, CONFIG['API Key'], appname), shell=True)
        temp = subprocess.call('{} API_SECRET_KEY={} {}'.format(cmd, CONFIG['API Secret Key'], appname), shell=True)
        temp = subprocess.call('{} ACCESS_TOKEN={} {}'.format(cmd, CONFIG['Access Token'], appname), shell=True)
        temp = subprocess.call('{} ACCESS_TOKEN_SECRET={} {}'.format(cmd, CONFIG['Access Token Secret'], appname), shell=True)
        temp = subprocess.call('{} LOG_NAME={} {}'.format(cmd, CONFIG['Target name in logs'], appname), shell=True)
        temp = subprocess.call('{} TARGET={} {}'.format(cmd, CONFIG['Target account handle'], appname), shell=True)
        temp = subprocess.call('{} URL_NUMBER={} {}'.format(cmd, CONFIG['Tweet URL location'], appname), shell=True)
        temp = subprocess.call('{} WHERE={} {}'.format(cmd, CONFIG['Target image location on site'], appname), shell=True)
        temp = subprocess.call('{} LOG_NAME={} {}'.format(cmd, CONFIG['Your account handle'], appname), shell=True)
        # This one identifies if the bot is running locally or on Heroku
        temp = subprocess.call('{} XKCD_APPNAME={} {}'.format(cmd, CONFIG['Heroku bot name'], appname), shell=True)