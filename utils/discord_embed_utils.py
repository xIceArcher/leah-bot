import datetime

import discord
from discord import Embed
from regex import regex

from utils.twitter_utils import extract_text, get_tweet_url, extract_photo_urls, get_profile_url, is_reply, \
    get_user, is_quote, is_retweet, get_hashtag_url, extract_main_photo_url
from utils.url_utils import unpack_short_link


def get_tweet_embeds(tweet, color: int = None):
    embeds = [get_main_tweet_embed(tweet, color)] + get_remaining_photo_embeds(tweet, color)

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

    embed.description = fix_tweet_text(embed.description, tweet)

    embed.set_author(name=f'{tweet.user.name} (@{tweet.user.screen_name})',
                     url=get_profile_url(tweet.user),
                     icon_url=tweet.user.profile_image_url_https)

    return embed


def get_standard_tweet_embed(tweet):
    embed = Embed(url=get_tweet_url(tweet),
                  title=f'Tweet by {tweet.user.name}',
                  description=extract_text(tweet))

    photo_url = extract_main_photo_url(tweet)

    if photo_url:
        embed.set_image(url=photo_url)

    return embed


def get_reply_tweet_embed(tweet):
    replied_user = get_user(screen_name=tweet.in_reply_to_screen_name)
    escaped_screen_name = replied_user.screen_name.replace('_', '\_')

    embed = Embed(url=get_tweet_url(tweet),
                  title=f'Reply to {replied_user.name} (@{escaped_screen_name})',
                  description=extract_text(tweet))

    photo_url = extract_main_photo_url(tweet)

    if photo_url:
        embed.set_image(url=photo_url)

    return embed


def get_quoted_tweet_embed(tweet):
    quoted_tweet = tweet.quoted_status

    embed = Embed(url=get_tweet_url(tweet),
                  title=f'Tweet by {tweet.user.name}',
                  description=extract_text(tweet))

    screen_name = quoted_tweet.user.screen_name
    author_text = f'Quoted tweet by {quoted_tweet.user.name} (@{screen_name})'
    quoted_link = get_tweet_url(quoted_tweet)
    author_info = get_named_link(author_text, quoted_link) + '\n'

    quoted_text = extract_text(quoted_tweet)

    embed.add_field(name=f'Quote',
                    value=author_info + fix_tweet_text(quoted_text, quoted_tweet),
                    inline=False)

    original_photo_urls = extract_photo_urls(tweet)
    quoted_photo_urls = extract_photo_urls(quoted_tweet)

    if original_photo_urls:
        embed.set_image(url=original_photo_urls[0])
    elif quoted_photo_urls:
        embed.set_image(url=quoted_photo_urls[0])

    return embed


def get_retweet_embed(tweet):
    retweet = tweet.retweeted_status

    escaped_screen_name = retweet.user.screen_name.replace('_', '\_')
    embed = Embed(url=get_tweet_url(tweet),
                  title=f'Retweeted {retweet.user.name} (@{escaped_screen_name})',
                  description=extract_text(retweet))

    photo_url = extract_main_photo_url(retweet)

    if photo_url:
        embed.set_image(url=photo_url)

    return embed


def get_remaining_photo_embeds(tweet, color: int = None):
    embeds = []

    if is_retweet(tweet):
        photo_urls = extract_photo_urls(tweet.retweeted_status)
    else:
        photo_urls = extract_photo_urls(tweet)

    if photo_urls and len(photo_urls) > 1:
        for photo_url in photo_urls[1:]:
            embeds.append(get_photo_embed(photo_url, color=color))

    return embeds


def get_user_embed(user, color: int = None):
    icon_url = user.profile_image_url_https.replace('_normal', '')
    banner_url = f'{user.profile_banner_url}/1500x500'

    embed = Embed(description=fix_user_text(user.description, user))
    embed.set_thumbnail(url=icon_url)
    embed.set_author(name=f'{user.name} (@{user.screen_name})',
                     url=get_profile_url(user),
                     icon_url=icon_url)

    embed.set_image(url=banner_url)

    embed.set_footer(text='Twitter',
                     icon_url='https://abs.twimg.com/icons/apple-touch-icon-192x192.png')
    embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)

    if color:
        embed.colour = color

    embed.add_field(name="Tweets", value=user.statuses_count, inline=True)
    embed.add_field(name="Followers", value=user.followers_count, inline=True)
    embed.add_field(name="Following", value=user.friends_count, inline=True)

    return embed


def get_photo_embed(url: str, color: int = None):
    return Embed(color=color).set_image(url=url) if color else Embed().set_image(url=url)


def get_color_embed(message: str, color: int):
    return Embed(description=message, color=color)


def fix_tweet_text(text: str, tweet):
    if is_retweet(tweet):
        tweet = tweet.retweeted_status

    # Order of operations here is important
    # (1) Fixing hashtags: Depends on string index, so must be first
    # (2) Fix escape characters
    # (3) Adding mention URLs and expanding short links: Might have '_' or '~', must be after (2)

    text = replace_hashtag_with_link(text, tweet.entities.get('hashtags'))

    text = fix_escape_characters(text)

    if is_reply(tweet):
        text = replace_mention_with_link(text, tweet.entities.get('user_mentions'), tweet.in_reply_to_screen_name)
    else:
        text = replace_mention_with_link(text, tweet.entities.get('user_mentions'))

    text = expand_short_links(text, tweet.entities.get('urls'))

    text = delete_media_links(text, tweet.entities.get('media'))
    text = delete_quote_links(text, tweet)

    return text.strip()


def fix_user_text(text: str, user):
    text = replace_hashtag_with_link(text)
    text = fix_escape_characters(text)
    text = expand_short_links(text, user.entities['description']['urls'])

    return text.strip()


def fix_escape_characters(text: str):
    text = text.replace('&amp;', '\&')
    text = text.replace('&lt;', '\<')
    text = text.replace('&gt;', '\>')

    # Escape Discord's markdown
    text = text.replace('`', '\`')
    text = text.replace('*', '\*')
    text = text.replace('~', '\~')

    # Special exception for underscore because Twitter user names may contain them
    text = regex.sub(r'(?<!@\S*)_', '\_', text)

    return text


def replace_hashtag_with_link(text: str, hashtag_entities=None):
    if hashtag_entities is not None:
        hashtags_sorted = sorted(hashtag_entities, key=lambda x: x['indices'][0], reverse=True)

        for hashtag in hashtags_sorted:
            start, end = hashtag['indices']

            # text[start] is either '#' or '＃', so this preserves the original character used
            hashtag_text = text[start] + hashtag['text']
            text = text[0:start] + get_named_link(hashtag_text, get_hashtag_url(hashtag_text)) + text[end:]
    else:
        hashtags = regex.findall(r'(?:[#|＃])[^\d\W][\w]*', text)
        for hashtag in hashtags:
            text = regex.sub(regex.escape(hashtag), fr'{get_named_link(hashtag, get_hashtag_url(hashtag))}', text)

    return text


def replace_mention_with_link(text: str, user_mentions_entities, in_reply_to_screen_name: str = None):
    if not user_mentions_entities:
        return text

    for mention in user_mentions_entities:
        mention_text = '@' + mention['screen_name']

        if in_reply_to_screen_name and mention['screen_name'] == in_reply_to_screen_name:
            text = regex.sub(regex.escape(mention_text), '', text, flags=regex.IGNORECASE)
        else:
            text = text.replace(mention_text,
                                get_named_link(mention_text, get_profile_url(screen_name=mention['screen_name'])))

    return text


def expand_short_links(text: str, urls_entities):
    if not urls_entities:
        return text

    for url in urls_entities:
        text = text.replace(url['url'], unpack_short_link(url['expanded_url']))

    return text


def delete_media_links(text: str, media_entities):
    if not media_entities:
        return text

    try:
        for media in media_entities:
            text = text.replace(media['url'], '')
    except AttributeError:
        pass

    return text


def delete_quote_links(text: str, tweet):
    if is_quote(tweet):
        text = regex.sub(get_tweet_url(tweet.quoted_status), '', text, flags=regex.IGNORECASE)

    return text


def get_named_link(text: str, link: str):
    return f'[{text}]({link})'


def add_tweet_footer(self: discord.Embed, tweet):
    self.set_footer(text='Twitter',
                    icon_url='https://abs.twimg.com/icons/apple-touch-icon-192x192.png')

    self.timestamp = tweet.created_at


discord.Embed.add_tweet_footer = add_tweet_footer
