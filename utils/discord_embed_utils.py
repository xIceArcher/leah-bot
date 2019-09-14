from discord import Embed

from utils.twitter_utils import extract_text, get_tweet_url, extract_photo_urls, get_profile_url, get_tweet


def get_tweet_embed(id: int, color: int = None):
    tweet = get_tweet(id)

    if color:
        embed = Embed(title=f'Tweet by {tweet.user.name}',
                      description=extract_text(tweet),
                      url=get_tweet_url(tweet),
                      color=color)
    else:
        embed = Embed(title=f'Tweet by {tweet.user.name}',
                      description=extract_text(tweet),
                      url=get_tweet_url(tweet))

    embed.timestamp = tweet.created_at

    embed.set_author(name=f'{tweet.user.name} (@{tweet.user.screen_name})',
                     url=get_profile_url(tweet.user),
                     icon_url=tweet.user.profile_image_url_https)

    embed.set_footer(text='Twitter',
                     icon_url='https://abs.twimg.com/icons/apple-touch-icon-192x192.png')

    photos = extract_photo_urls(tweet)

    if photos:
        embed.set_image(url=photos[0])

    return embed


def get_photo_embed(url):
    return Embed().set_image(url=url)
