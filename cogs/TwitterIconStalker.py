import datetime
import re

from discord import Embed
from discord.ext import commands

from utils.discord_embed_utils import get_named_link
from utils.twitter_utils import get_user, get_profile_url, get_hashtag_url


class TwitterIconStalker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def user(self, ctx, screen_name):
        user = get_user(screen_name=screen_name)

        if user is None:
            await ctx.channel.send(f'User @{screen_name} does not exist!')
            return

        big_icon_url = user.profile_image_url_https.replace('_normal', '')
        banner_url = f'{user.profile_banner_url}/1500x500'
        description = user.description

        hashtags = re.findall(r'(?:[#|＃])[^\d\W][\w]*', description)
        for hashtag in hashtags:
            description = re.sub(fr'{hashtag}', fr'{get_named_link(hashtag, get_hashtag_url(hashtag))}', description)

        embed = Embed(description=description)

        embed.set_author(name=f'{user.name} (@{user.screen_name})',
                         url=get_profile_url(user),
                         icon_url=user.profile_image_url_https)
        embed.set_image(url=banner_url)
        embed.set_footer(text='Twitter',
                         icon_url='https://abs.twimg.com/icons/apple-touch-icon-192x192.png')

        embed.set_thumbnail(url=big_icon_url)
        embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)

        embed.add_field(name="Tweets", value=user.statuses_count, inline=True)
        embed.add_field(name="Followers", value=user.followers_count, inline=True)
        embed.add_field(name="Following", value=user.friends_count, inline=True)

        await ctx.channel.send(embed=embed)


def setup(bot):
    bot.add_cog(TwitterIconStalker(bot))
