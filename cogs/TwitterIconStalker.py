import logging

from discord.ext import commands

from utils.discord_embed_utils import get_user_embed
from utils.twitter_utils import get_user

logger = logging.getLogger(__name__)


class TwitterIconStalker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def user(self, ctx, screen_name):
        user = get_user(screen_name=screen_name)

        if user is None:
            await ctx.channel.send(f'User @{screen_name} does not exist!')
            return

        embed = get_user_embed(user)

        await ctx.channel.send(embed=embed)
        logger.info(f'User @{screen_name} sent to channel #{ctx.channel.name} in {ctx.guild.name}')


def setup(bot):
    bot.add_cog(TwitterIconStalker(bot))
