import logging

from aiohttp import ClientConnectionError
from discord.ext import commands
from discord import Embed

from utils.discord_embed_utils import get_photo_embed
from utils.discord_utils import clean_message
from utils.instagram_utils import get_insta_post_info
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
            post_info = get_insta_post_info(link)

            embed = Embed(url=post_info['url'],
                          title=f"Instagram post by {post_info['full_name']}",
                          description=post_info['text'][:240] + ("..." if len(post_info['text']) else ""))
            
            embed.set_author(name=f"{post_info['full_name']} ({post_info['username']})",
                             url=f"https://instagram.com/{post_info['username']}",
                             icon_url=post_info['profile_pic_url'])

            embed.set_image(url=post_info['photos'][0])

            await message.channel.send(embed=embed)

            for photo in post_info['photos'][1:]:
                while True:
                    try:
                        await message.channel.send(embed=get_photo_embed(photo))
                        break
                    except ClientConnectionError:
                        pass

            logger.info(f"Instagram URL: {link}, Photos: {post_info['photos']}")

        await self.bot.process_commands(message)


def setup(bot):
    bot.add_cog(PostInstaMedia(bot))
