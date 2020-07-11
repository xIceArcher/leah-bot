import logging
from datetime import datetime
from pytz import timezone

from discord.ext import commands
from discord import Embed

logger = logging.getLogger(__name__)


class PostTime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def jst(self, ctx, time_str: str, message = None):
        ts = timezone('Asia/Tokyo').localize(datetime.strptime(time_str, '%Y/%m/%d %H%M'))

        embed = Embed(title=message)
        embed.timestamp = ts
        embed.set_footer(text='Time in your local timezone')
        embed.color = int('FF0000', base=16)

        await ctx.channel.send(embed=embed)


def setup(bot):
    bot.add_cog(PostTime(bot))
