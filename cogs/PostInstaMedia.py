import logging

from aiohttp import ClientConnectionError
from discord.ext import commands

from utils.discord_utils import clean_message
from utils.discord_embed_utils import get_photo_embed
from utils.discord_embed_insta_utils import get_insta_embeds, get_insta_video_urls
from utils.url_utils import get_insta_ids

logger = logging.getLogger(__name__)


class PostInstaMedia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.content.startswith(self.bot.command_prefix):
            return

        cleaned_message = clean_message(message.content)

        for insta_id in get_insta_ids(cleaned_message):
            embeds = get_insta_embeds(insta_id)

            for embed in embeds:
                while True:
                    try:
                        await message.channel.send(embed=embed)
                        break
                    except ClientConnectionError:
                        pass

            video_urls = get_insta_video_urls(insta_id)

            if video_urls:
                for video_url in video_urls:
                    await message.channel.send(video_url)

            logger.info(f"Instagram ID: {insta_id} sent")

        await self.bot.process_commands(message)


def setup(bot):
    bot.add_cog(PostInstaMedia(bot))
