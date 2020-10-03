import logging
from utils.line_utils import get_line_live_m3u8_links

from discord.ext import commands

logger = logging.getLogger(__name__)


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def linelive(self, ctx, broadcast_link):
        m3u8_links = get_line_live_m3u8_links(broadcast_link)
        HELP_MESSAGE = 'These magic links can be used with **MPV/Streamlink**\n'

        if m3u8_links is None:
            await ctx.channel.send('No links found. This command will only work ~5 minutes before the broadcast begins.')
        else:
            best_m3u8, abr_m3u8 = m3u8_links
            await ctx.channel.send(HELP_MESSAGE + f"**Best resolution** (use this in general): {best_m3u8}\n"
                                                  f"**Adaptive resolution** (use this if your connection might be slow): {abr_m3u8}")

def setup(bot):
    bot.add_cog(Admin(bot))
