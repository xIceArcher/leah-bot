import datetime
import logging

import discord
from discord import Embed

from utils.discord_embed_utils import get_photo_embed
from utils.instagram_utils import get_insta_post, get_insta_post_url, get_insta_user_url, \
    extract_full_name, extract_username, extract_profile_pic_url, \
    extract_likes, extract_timestamp, extract_photos, extract_text, \
    extract_videos


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

    main_embed = Embed(url=get_insta_post_url(shortcode),
                       title=f'Instagram post by {extract_full_name(user_info_source)}',
                       description=extract_text(post, max_length=240))

    main_embed.set_author(name=f'{extract_full_name(user_info_source)} ({extract_username(user_info_source)})',
                          url=f'{get_insta_user_url(user_info_source)}',
                          icon_url=extract_profile_pic_url(user_info_source))

    main_embed.color = INSTA_COLOR
    main_embed.add_field(name="Likes", value=extract_likes(post), inline=True)

    photos = extract_photos(post)
    main_embed.set_image(url=photos[0])

    embeds.append(main_embed)

    for photo in photos[1:]:
        embeds.append(get_photo_embed(photo, color=INSTA_COLOR))

    embeds[-1].add_insta_footer(post)
    return embeds


async def get_insta_video_urls(shortcode: str=None, post: dict=None):
    if post is None:
        post = await get_insta_post(shortcode)

    return extract_videos(post)


def add_insta_footer(self: discord.Embed, post):
    self.set_footer(text='Instagram',
                    icon_url='https://instagram-brand.com/wp-content/uploads/2016/11/Instagram_AppIcon_Aug2017.png?w=300')

    self.timestamp = extract_timestamp(post)


discord.Embed.add_insta_footer = add_insta_footer
