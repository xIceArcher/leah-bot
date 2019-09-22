import logging

from discord.ext import commands

from utils.ameblo_utils import get_ameblo_photo_urls
from utils.discord_embed_utils import get_photo_embed
from utils.discord_utils import clean_message
from utils.url_utils import get_ameblo_links

logger = logging.getLogger(__name__)


class PostAmebloMedia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.content.startswith(self.bot.command_prefix):
            return

        cleaned_message = clean_message(message.content)

        for link in get_ameblo_links(cleaned_message):
            photos = get_ameblo_photo_urls(link)[1:]

            for photo in photos:
                await message.channel.send(embed=get_photo_embed(photo))

            logger.info(f'Ameblo URL: {link}, Photos: {photos}')

        await self.bot.process_commands(message)


def setup(bot):
    bot.add_cog(PostAmebloMedia(bot))
