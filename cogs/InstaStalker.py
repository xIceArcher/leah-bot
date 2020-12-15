import asyncio
import json
import logging
import os
import time

from aiohttp import ClientConnectionError
from discord.ext import commands, tasks

from utils.instagram_utils import get_insta_timeline, extract_post_count, extract_recent_posts
from utils.discord_embed_insta_utils import get_insta_embeds, get_insta_video_urls

logger = logging.getLogger(__name__)


class InstaStalker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stalk_destinations = {}
        self.last_post_count = {}

        self.load_destinations()
        self.setup_last_post_count()

        self.discord_poster.start()

    def load_destinations(self):
        path = os.path.join(os.getcwd(), 'data', 'insta.json')
        with open(path) as f:
            self.stalk_destinations = json.load(f)

    def save_destinations(self):
        path = os.path.join(os.getcwd(), 'data', 'insta.json')
        with open(path, 'w') as f:
            f.seek(0)
            json.dump(self.stalk_destinations, f, indent=4)

    def setup_last_post_count(self):
        for user_id in self.stalk_destinations:
            user_timeline = get_insta_timeline(user_id)
            self.last_post_count[user_id] = extract_post_count(user_timeline)

            logger.info(f'User {user_id} has {extract_post_count(user_timeline)} posts')
            time.sleep(5)

    @tasks.loop(hours=6.0)
    async def discord_poster(self):
        for user_id in self.stalk_destinations:
            user_timeline = get_insta_timeline(user_id)
            curr_post_count = extract_post_count(user_timeline)

            if self.last_post_count[user_id] < curr_post_count:
                num_posts_to_fetch = curr_post_count - self.last_post_count[user_id]
                new_posts = extract_recent_posts(user_timeline, max_posts=num_posts_to_fetch)
                new_posts.reverse()

                for post in new_posts:
                    post_id = post['shortcode']
                    embeds = get_insta_embeds(post=post, user=user_timeline)
                    video_urls = get_insta_video_urls(post=post)

                    for channel_id in self.stalk_destinations[user_id]:
                        channel = self.bot.get_channel(channel_id)

                        for embed in embeds:
                            while True:
                                try:
                                    await channel.send(embed=embed)
                                    break
                                except ClientConnectionError:
                                    pass

                        if video_urls:
                            for video_url in video_urls:
                                await channel.send(video_url)

                    logger.info(f'Instagram ID: {post_id} sent to {channel.name} in {channel.guild.name}')

            await asyncio.sleep(10)

    def cog_unload(self):
        self.discord_poster.cancel()
        self.save_destinations()

    @discord_poster.before_loop
    async def await_ready(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(InstaStalker(bot))
