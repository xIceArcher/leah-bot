import logging

from discord.ext import commands

from utils.discord_embed_youtube_utils import get_youtube_livestream_embed
from utils.url_utils import get_youtube_video_ids

from utils.discord_utils import clean_message

logger = logging.getLogger(__name__)


class PostYoutubeInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.content.startswith(self.bot.command_prefix):
            return

        if message.channel.id != 690903288459034675 and message.channel.id != 611545994890313738:
            return

        cleaned_message = clean_message(message.content)

        for video_id in get_youtube_video_ids(cleaned_message):
            embed = get_youtube_livestream_embed(video_id, only_livestream=True)
            await message.channel.send(embed=embed)

            logger.info(f"Youtube video ID: {video_id} sent to {message.channel.name} in {message.guild.name}")

        await self.bot.process_commands(message)


def setup(bot):
    bot.add_cog(PostYoutubeInfo(bot))
