import logging

from discord.ext import commands

from utils.twitter_utils import extract_photo_urls, get_tweet
from utils.url_utils import get_tweet_ids

logger = logging.getLogger(__name__)

MAX_MEDIA_COUNT = 5


class PostTweetMedia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def photos(self, ctx, twitter_url: str):
        tweet_ids = get_tweet_ids(twitter_url)

        if len(tweet_ids) == 0:
            await ctx.channel.send("Message does not contain a Twitter link!")
            return

        tweet = get_tweet(tweet_ids[0])
        photos = extract_photo_urls(tweet)

        if len(photos) == 0:
            await ctx.channel.send("Tweet does not have any photos!")
            return

        logger.info(f'Twitter URL: {twitter_url}, Tweet ID: {tweet_ids[0]}, Photos: {photos}')

        for photo in photos:
            await ctx.channel.send(photo)


def setup(bot):
    bot.add_cog(PostTweetMedia(bot))
