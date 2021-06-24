import logging

import discord
from discord import Embed
from regex import regex

from utils.discord_embed_utils import get_photo_embed, get_named_link
from utils.instagram_utils import get_insta_post, get_insta_post_url, get_insta_user_url, \
    extract_full_name, extract_username, extract_profile_pic_url, \
    extract_likes, extract_timestamp, extract_photos, extract_text, \
    extract_videos, get_hashtag_url, get_mention_url


logger = logging.getLogger(__name__)
INSTA_COLOR = int('CE0072', base=16)

async def get_insta_embeds(shortcode: str=None, post: dict=None, user: dict=None):
    if post is None:
        post = await get_insta_post(shortcode)

    if shortcode is None:
        shortcode = post['shortcode']

    if post is None and shortcode is None:
        return []

    user_info_source = user if user is not None else post['owner']

    embeds = []
    text_posts = populate_links(extract_text(post), 2048)

    main_embed = Embed(url=get_insta_post_url(shortcode),
                       title=f'Instagram post by {extract_full_name(user_info_source)}',
                       description=text_posts[0])

    main_embed.set_author(name=f'{extract_full_name(user_info_source)} ({extract_username(user_info_source)})',
                          url=f'{get_insta_user_url(user_info_source)}',
                          icon_url=extract_profile_pic_url(user_info_source))
    main_embed.color = INSTA_COLOR
    embeds.append(main_embed)

    for text_post in text_posts[1:]:
        text_embed = Embed(description=text_post)
        text_embed.color = INSTA_COLOR
        embeds.append(text_embed)

    embeds[-1].add_field(name="Likes", value=extract_likes(post), inline=True)

    photos = extract_photos(post)
    embeds[-1].set_image(url=photos[0])

    for photo in photos[1:]:
        embeds.append(get_photo_embed(photo, color=INSTA_COLOR))

    embeds[-1].add_insta_footer(post)
    return embeds


async def get_insta_video_urls(shortcode: str=None, post: dict=None):
    if post is None:
        post = await get_insta_post(shortcode)

    return extract_videos(post)


def populate_links(full_text: str, max_post_length: int):
    funcs = [(get_mentions, get_mention_url), (get_hashtags, get_hashtag_url)]

    entities = []
    for get_func, url_func in funcs:
        entities.extend([(start, start + len(text), text, lambda x: get_named_link(x, url_func(x))) for start, text in get_func(full_text)])
    entities.sort(reverse=True)

    split_posts = ['']
    if entities and entities[-1][0] == 0:
        curr_entity = entities.pop()
    elif entities:
        end_pos = min(max_post_length, entities[-1][0])
        curr_entity = (0, end_pos, full_text[0:end_pos], lambda x: x)
    else:
        curr_entity = (0, max_post_length, full_text[0:max_post_length], lambda x: x)

    while True:
        _, next_start_pos, curr_text, func = curr_entity

        if len(split_posts[-1]) + len(func(curr_text)) > max_post_length:
            split_posts.append('')
        split_posts[-1] += func(curr_text)

        if next_start_pos == len(full_text):
            break
        elif entities and next_start_pos == entities[-1][0]:
            curr_entity = entities.pop()
        else:
            # The next entity is free-running text
            # 3 cases: all the way to the end, until this post is full, or until the start of the next entity
            next_end_pos = min(len(full_text), next_start_pos + (max_post_length - len(split_posts[-1])))
            if entities:
                next_end_pos = min(next_end_pos, entities[-1][0])

            curr_entity = (next_start_pos, next_end_pos, full_text[next_start_pos:next_end_pos], lambda x: x)

    return split_posts

def get_mentions(text: str):
    mentions = regex.findall(r'(?:[@|＠])[^\d\W][\w]*', text)
    mentions.sort(key=lambda x: len(x))

    idx_mention_map = {}

    for mention in mentions:
        indices = [m.start(0) for m in regex.finditer(regex.escape(mention), text)]
        for idx in indices:
            idx_mention_map[idx] = mention

    return idx_mention_map.items()


def get_hashtags(text: str):
    hashtags = regex.findall(r'(?:[#|＃])[^\d\W][\w]*', text)
    hashtags.sort(key=lambda x: len(x))

    idx_hashtag_map = {}

    for hashtag in hashtags:
        indices = [m.start(0) for m in regex.finditer(regex.escape(hashtag), text)]
        for idx in indices:
            idx_hashtag_map[idx] = hashtag

    return idx_hashtag_map.items()

def add_insta_footer(self: discord.Embed, post):
    self.set_footer(text='Instagram',
                    icon_url='https://instagram-brand.com/wp-content/uploads/2016/11/Instagram_AppIcon_Aug2017.png?w=300')

    self.timestamp = extract_timestamp(post)


discord.Embed.add_insta_footer = add_insta_footer
