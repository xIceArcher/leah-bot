import re

import discord
from discord import Embed

from utils.twitter_utils import extract_text, get_tweet_url, extract_photo_urls, get_profile_url, is_reply, \
    get_user, is_quote, is_retweet, is_standard, get_hashtag_url


def get_tweet_embeds(tweet, color: int = None):
    embeds = [get_main_tweet_embed(tweet, color)]

    if is_standard(tweet) or is_reply(tweet):
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
    if is_reply(tweet):
        embed = get_reply_tweet_embed(tweet)
    elif is_retweet(tweet):
        embed = get_retweet_embed(tweet)
    elif is_quote(tweet):
        embed = get_quoted_tweet_embed(tweet)
    else:
        embed = get_standard_tweet_embed(tweet)

    if color:
        embed.colour = color

    embed.description = populate_links(embed.description)

    embed.set_author(name=f'{tweet.user.name} (@{tweet.user.screen_name})',
                     url=get_profile_url(tweet.user),
                     icon_url=tweet.user.profile_image_url_https)

    return embed


def get_standard_tweet_embed(tweet):
    embed = Embed(url=get_tweet_url(tweet),
                  title=f'Tweet by {tweet.user.name}',
                  description=extract_text(tweet))

    photos = extract_photo_urls(tweet)

    if photos:
        embed.set_image(url=photos[0])

    return embed


def get_reply_tweet_embed(tweet):
    replied_user = get_user(screen_name=tweet.in_reply_to_screen_name)

    return Embed(url=get_tweet_url(tweet),
                 title=f'Reply to {replied_user.name} (@{replied_user.screen_name})',
                 description=re.sub(f'@{replied_user.screen_name}', '', extract_text(tweet), flags=re.IGNORECASE))


def get_quoted_tweet_embed(tweet):
    quoted_tweet = tweet.quoted_status

    embed = Embed(url=get_tweet_url(tweet),
                  title=f'Tweet by {tweet.user.name}',
                  description=re.sub(get_tweet_url(quoted_tweet), '', extract_text(tweet), flags=re.IGNORECASE))

    author_text = f'Quoted tweet by {quoted_tweet.user.name} (@{quoted_tweet.user.screen_name})'
    quoted_link = get_tweet_url(quoted_tweet)
    author_info = get_named_link(author_text, quoted_link) + '\n'

    quoted_text = extract_text(quoted_tweet)

    embed.add_field(name=f'Quote',
                    value=author_info + populate_links(quoted_text),
                    inline=False)

    photo_urls = extract_photo_urls(quoted_tweet)

    if photo_urls:
        embed.set_image(url=photo_urls[0])

    return embed


def get_retweet_embed(tweet):
    retweet = tweet.retweeted_status

    embed = Embed(url=get_tweet_url(tweet),
                  title=f'Retweeted {retweet.user.name} (@{retweet.user.screen_name})',
                  description=extract_text(retweet))

    photo_urls = extract_photo_urls(retweet)

    if photo_urls:
        embed.set_image(url=photo_urls[0])

    return embed


def get_photo_embed(url: str, color: int = None):
    return Embed(color=color).set_image(url=url) if color else Embed().set_image(url=url)


def get_color_embed(message: str, color: int):
    return Embed(description=message, color=color)


def get_named_link(text: str, link: str):
    return f'[{text}]({link})'


def replace_mention_with_link(text: str):
    mentions = re.findall(r'@[^ \r\n]*', text)

    for mention in mentions:
        text = text.replace(mention, get_named_link(mention, get_profile_url(screen_name=mention[1:])))

    return text


def replace_hashtag_with_link(text: str):
    hashtags = re.findall(r'#[^ \r\n]*', text)

    for hashtag in hashtags:
        text = text.replace(hashtag, get_named_link(hashtag, get_hashtag_url(hashtag)))

    return text


def populate_links(text: str):
    text = replace_mention_with_link(text)
    text = replace_hashtag_with_link(text)

    return text


def add_tweet_footer(self: discord.Embed, tweet):
    self.set_footer(text='Twitter',
                    icon_url='https://abs.twimg.com/icons/apple-touch-icon-192x192.png')

    self.timestamp = tweet.created_at


discord.Embed.add_tweet_footer = add_tweet_footer
