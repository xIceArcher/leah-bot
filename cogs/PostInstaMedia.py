import logging

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

            for photo in photos:
                await message.channel.send(embed=get_photo_embed(photo))

            logger.info(f'Instagram URL: {link}, Photos: {photos}')

        await self.bot.process_commands(message)

    @commands.command()
    @commands.is_owner()
    async def insta(self, ctx, insta_url: str):
        for photo in get_insta_photo_urls(insta_url):
            await ctx.channel.send(embed=get_photo_embed(photo))


def setup(bot):
    bot.add_cog(PostInstaMedia(bot))
