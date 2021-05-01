import logging
from queue import Queue
import asyncio

from aiohttp import ClientConnectionError
from discord.ext import commands, tasks

from utils.discord_utils import clean_message
from utils.discord_embed_insta_utils import get_insta_embeds, get_insta_video_urls, get_insta_post_url
from utils.instagram_utils import get_insta_post
from utils.url_utils import get_insta_shortcodes

logger = logging.getLogger(__name__)


class PostInstaMedia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.insta_queue = Queue()

        self.discord_poster.start()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.content.startswith(self.bot.command_prefix):
            return

        cleaned_message = clean_message(message.content)

        for shortcode in get_insta_shortcodes(cleaned_message):
            self.insta_queue.put((shortcode, message))

        await self.bot.process_commands(message)

    @tasks.loop(seconds=1.0)
    async def discord_poster(self):
        if not self.insta_queue.empty():
            shortcode, message = self.insta_queue.get()
            post = get_insta_post(shortcode)
            embeds = get_insta_embeds(post=post)

            for embed in embeds:
                while True:
                    try:
                        await message.channel.send(embed=embed)
                        break
                    except ClientConnectionError:
                        pass

            video_urls = get_insta_video_urls(post=post)

            if video_urls:
                for video_url in video_urls:
                    await message.channel.send(video_url)

            logger.info(f"{get_insta_post_url(shortcode)} sent to #{message.channel.name} in {message.guild.name}")
            await asyncio.sleep(10)


def setup(bot):
    bot.add_cog(PostInstaMedia(bot))
