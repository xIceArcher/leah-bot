from dateutil import parser
from datetime import datetime, timezone, timedelta
import logging

import discord
from discord import Embed
from regex import regex

from utils.youtube_utils import get_video, get_channel, get_video_url, get_channel_url, is_livestream
from utils.utils import format_time_delta

logger = logging.getLogger(__name__)

def get_youtube_livestream_embed(video_id: str, only_livestream=True):
    video_info = get_video(video_id, parts=['liveStreamingDetails'])

    channel_id = video_info['snippet']['channelId']
    channel_info = get_channel(channel_id)

    if is_livestream(video_info):
        embed = Embed(url=get_video_url(video_id),
                      title=video_info['snippet']['title'])

        embed.set_thumbnail(url=video_info['snippet']['thumbnails']['default']['url'])

        embed.set_author(name=video_info['snippet']['channelTitle'],
                         url=get_channel_url(channel_id),
                         icon_url=channel_info['snippet']['thumbnails']['default']['url'])

        start_time = parser.isoparse(video_info['liveStreamingDetails']['scheduledStartTime'])
        embed.timestamp = start_time

        if datetime.now(timezone.utc) - start_time > timedelta(0):
            embed.add_field(name='Started', value=f'{format_time_delta(datetime.now(timezone.utc) - start_time)} ago')
            embed.color = int('FF0000', base=16)
        else:
            time_to_start = start_time - datetime.now(timezone.utc)
            embed.add_field(name='Starts in', value=format_time_delta(time_to_start))

            if time_to_start < timedelta(hours=1):
                embed.color = int('FF9300', base=16)
            else:
                embed.color = int('00FF00', base=16)

        embed.set_footer(text='YouTube',
                         icon_url='https://cdn4.iconfinder.com/data/icons/social-media-2210/24/Youtube-512.png')

        return embed

    return None
