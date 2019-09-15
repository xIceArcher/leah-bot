import discord
from discord import Embed

from utils.twitter_utils import extract_text, get_tweet_url, extract_photo_urls, get_profile_url, get_tweet


def get_tweet_embeds(tweet_id: int, color: int = None):
    tweet = get_tweet(tweet_id)
    embeds = [get_main_tweet_embed(tweet, color)]

    photo_urls = extract_photo_urls(tweet)

    try:
        photo_urls.pop(0)
    except (AttributeError, IndexError):
        pass

    if photo_urls:
        for photo_url in photo_urls:
            embeds.append(get_photo_embed(photo_url, color=color))

    embeds[-1].add_tweet_footer(tweet)

    return embeds


def get_main_tweet_embed(tweet, color: int = None):
    if color:
        embed = Embed(title=f'Tweet by {tweet.user.name}',
                      description=extract_text(tweet),
                      url=get_tweet_url(tweet),
                      color=color)
    else:
        embed = Embed(title=f'Tweet by {tweet.user.name}',
                      description=extract_text(tweet),
                      url=get_tweet_url(tweet))

    embed.set_author(name=f'{tweet.user.name} (@{tweet.user.screen_name})',
                     url=get_profile_url(tweet.user),
                     icon_url=tweet.user.profile_image_url_https)

    photos = extract_photo_urls(tweet)

    if photos:
        embed.set_image(url=photos[0])

    return embed


def get_photo_embed(url: str, color: int = None):
    return Embed(color=color).set_image(url=url) if color else Embed().set_image(url=url)


def add_tweet_footer(self: discord.Embed, tweet):
    self.set_footer(text='Twitter',
                    icon_url='https://abs.twimg.com/icons/apple-touch-icon-192x192.png')

    self.timestamp = tweet.created_at


discord.Embed.add_tweet_footer = add_tweet_footer
