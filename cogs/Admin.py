import logging

from discord.ext import commands

logger = logging.getLogger(__name__)


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def admin(self, ctx):
        await ctx.channel.send(f"Active servers: {[guild.name for guild in self.bot.guilds]}")


def setup(bot):
    bot.add_cog(Admin(bot))
