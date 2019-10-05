import tweepy
from tweepy import TweepError

from utils.credentials_utils import get_credentials
from utils.url_utils import get_photo_url

tweepy_api = None


def init_tweepy(credentials_file='credentials.json'):
    global tweepy_api

    credentials = get_credentials(credentials_file)

    auth = tweepy.OAuthHandler(credentials['twitter']['consumerKey'], credentials['twitter']['consumerSecret'])
    auth.set_access_token(credentials['twitter']['accessToken'], credentials['twitter']['accessTokenSecret'])

    tweepy_api = tweepy.API(auth)


def get_tweepy():
    global tweepy_api

    if not tweepy_api:
        init_tweepy()

    return tweepy_api


def is_retweet(tweet):
    return hasattr(tweet, 'retweeted_status')


def is_quote(tweet):
    return hasattr(tweet, 'quoted_status')


def is_reply(tweet):
    return tweet.in_reply_to_user_id is not None


def is_standard(tweet):
    return not is_retweet(tweet) and not is_quote(tweet) and not is_reply(tweet)


def extract_text(tweet):
    if is_retweet(tweet):
        try:
            text = tweet.retweeted_status.full_text
        except AttributeError:
            text = tweet.retweeted_status.text
    else:
        try:
            text = tweet.full_text
        except AttributeError:
            text = tweet.text

    # Escape Discord's formatting
    text = text.replace('&amp;', '\&')
    text = text.replace('&lt;', '\<')
    text = text.replace('&gt;', '\>')

    return text


def extract_photo_urls(tweet):
    try:
        return [get_photo_url(x['media_url']) for x in tweet.extended_entities['media'] if x['type'] == 'photo']
    except (AttributeError, KeyError):
        return None


def extract_displayed_video_url(tweet):
    if is_retweet(tweet):
        return extract_video_url(tweet.retweeted_status)
    elif is_quote(tweet):
        return extract_video_url(tweet.quoted_status)
    else:
        return extract_video_url(tweet)


def extract_video_url(tweet):
    max_bitrate = -1
    max_url = None

    try:
        for video in tweet.extended_entities['media'][0]['video_info']['variants']:
            if video['content_type'] == 'video/mp4' and int(video['bitrate']) > max_bitrate:
                max_bitrate = int(video['bitrate'])
                max_url = video['url']

        return max_url
    except (AttributeError, KeyError, IndexError):
        return None


def extract_links(tweet):
    return [x['expanded_url'] for x in tweet.entities['urls']]


def get_tweet_url(tweet):
    return f'https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}'


def get_profile_url(user=None, screen_name=None):
    if not screen_name and not user:
        raise ValueError('At least one argument required')

    if user:
        return f'https://twitter.com/{user.screen_name}'

    return f'https://twitter.com/{screen_name}'


def get_hashtag_url(hashtag: str):
    if hashtag.startswith('#'):
        return f'https://twitter.com/hashtag/{hashtag[1:]}'

    return f'https://twitter.com/hashtag/{hashtag}'


def get_tweet(tweet_id: int):
    api = get_tweepy()

    return api.get_status(tweet_id, tweet_mode='extended')


def get_user(user_id=None, screen_name=None):
    api = get_tweepy()

    try:
        if user_id:
            return api.get_user(user_id=user_id)
        if screen_name:
            return api.get_user(screen_name=screen_name)
    except TweepError:
        return None

    return None
