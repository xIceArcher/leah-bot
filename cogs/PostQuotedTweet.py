import logging

from discord.ext import commands
from tweepy import TweepError

from utils.discord_embed_twitter_utils import get_tweet_embeds
from utils.twitter_utils import get_tweet, is_quote, get_tweet_url, extract_video_url
from utils.url_utils import get_tweet_ids

logger = logging.getLogger(__name__)


class PostQuotedTweet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def quoted(self, ctx, twitter_url: str):
        tweet_id = get_tweet_ids(twitter_url)[0]

        if not tweet_id:
            await ctx.channel.send('Not a valid Twitter URL!')

        tweet = None

        try:
            tweet = get_tweet(tweet_id)
        except TweepError:
            await ctx.channel.send(f'Tweet ID {tweet_id} is not valid!')

        if is_quote(tweet):
            quoted_tweet = get_tweet(tweet.quoted_status.id)

            for embed in get_tweet_embeds(quoted_tweet):
                await ctx.channel.send(embed=embed)

            video = extract_video_url(tweet.quoted_status)

            if video:
                await ctx.channel.send(video)

            logger.info(f'Tweet ID: {tweet_id}, Quoted Tweet: {get_tweet_url(tweet.quoted_status)}')
        else:
            await ctx.channel.send(f'This tweet does not quote any other tweet!')


def setup(bot):
    bot.add_cog(PostQuotedTweet(bot))
