import logging

from aiohttp import ClientConnectionError
from discord.ext import commands

from utils.discord_embed_utils import get_photo_embed
from utils.discord_utils import clean_message
from utils.instagram_utils import get_insta_photo_urls
from utils.url_utils import get_insta_links

logger = logging.getLogger(__name__)


class PostInstaMedia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.content.startswith(self.bot.command_prefix):
            return

        cleaned_message = clean_message(message.content)

        for link in get_insta_links(cleaned_message):
            photos = get_insta_photo_urls(link)

            if photos:
                for photo in photos:
                    while True:
                        try:
                            await message.channel.send(embed=get_photo_embed(photo))
                            break
                        except ClientConnectionError:
                            pass

                logger.info(f'Instagram URL: {link}, Photos: {photos}')

        await self.bot.process_commands(message)


def setup(bot):
    bot.add_cog(PostInstaMedia(bot))
