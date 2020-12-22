import logging

from discord.ext import commands

from utils.discord_embed_twitter_utils import get_tweet_embeds
from utils.twitter_utils import extract_photo_urls, extract_video_url, get_tweet, get_tweet_url
from utils.url_utils import get_tweet_ids

logger = logging.getLogger(__name__)

MAX_MEDIA_COUNT = 5


class PostTweetMedia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def embed(self, ctx, twitter_url: str):
        tweet_ids = get_tweet_ids(twitter_url)

        if len(tweet_ids) == 0:
            await ctx.channel.send("Message does not contain a Twitter link!")
            return

        tweet = get_tweet(tweet_ids[0])

        for embed in get_tweet_embeds(tweet):
            await ctx.channel.send(embed=embed)

        logger.info(f'{get_tweet_url(tweet)} sent to #{ctx.channel.name} in {ctx.guild.name}')

    @commands.command()
    async def photos(self, ctx, twitter_url: str):
        tweet_ids = get_tweet_ids(twitter_url)

        if len(tweet_ids) == 0:
            await ctx.channel.send("Message does not contain a Twitter link!")
            return

        tweet = get_tweet(tweet_ids[0])
        photos = extract_photo_urls(tweet)

        if not photos:
            await ctx.channel.send("Tweet does not have any photos!")
            return

        logger.info(f'{get_tweet_url(tweet)} sent to #{ctx.channel.name} in {ctx.guild.name}')

        for photo in photos[1:]:
            await ctx.channel.send(photo)

    @commands.command()
    async def video(self, ctx, twitter_url: str):
        tweet_ids = get_tweet_ids(twitter_url)

        if len(tweet_ids) == 0:
            await ctx.channel.send("Message does not contain a Twitter link!")
            return

        tweet = get_tweet(tweet_ids[0])
        video = extract_video_url(tweet)

        if video is None:
            await ctx.channel.send("Tweet does not have a video!")
            return

        logger.info(f'{get_tweet_url(tweet)} sent to #{ctx.channel.name} in {ctx.guild.name}')
        await ctx.channel.send(video)

def setup(bot):
    bot.add_cog(PostTweetMedia(bot))
