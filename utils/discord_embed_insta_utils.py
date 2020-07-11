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

def get_insta_embeds(id: str):
    post = get_insta_post(id)
    embeds = []

    main_embed = Embed(url=get_insta_post_url(id),
                       title=f'Instagram post by {extract_full_name(post)}',
                       description=extract_text(post, max_length=240))

    main_embed.set_author(name=f'{extract_full_name(post)} ({extract_username(post)})',
                          url=f'{get_insta_user_url(post)}',
                          icon_url=extract_profile_pic_url(post))

    main_embed.color = INSTA_COLOR
    main_embed.add_field(name="Likes", value=extract_likes(post), inline=True)

    photos = extract_photos(post)
    main_embed.set_image(url=photos[0])

    embeds.append(main_embed)

    for photo in photos[1:]:
        embeds.append(get_photo_embed(photo, color=INSTA_COLOR))

    embeds[-1].add_insta_footer(post)
    return embeds


def get_insta_video_urls(id: str):
    post = get_insta_post(id)

    return extract_videos(post)


def add_insta_footer(self: discord.Embed, post):
    self.set_footer(text='Instagram',
                    icon_url='https://instagram-brand.com/wp-content/uploads/2016/11/Instagram_AppIcon_Aug2017.png?w=300')

    self.timestamp = extract_timestamp(post)


discord.Embed.add_insta_footer = add_insta_footer
