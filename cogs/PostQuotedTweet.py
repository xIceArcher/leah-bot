from discord.ext import commands

from utils.discord_utils import clean_message
from utils.twitter_utils import get_tweet, is_quote, get_tweet_url
from utils.url_utils import get_tweet_ids


class PostQuotedTweet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if self.bot.command_prefix == message.content[0:len(self.bot.command_prefix)]:
            return

        cleaned_message = clean_message(message.content)

        for tweet_id in get_tweet_ids(cleaned_message):
            tweet = get_tweet(tweet_id)

            if is_quote(tweet):
                await message.channel.send(f'Quoted Tweet: {get_tweet_url(tweet.quoted_status)}')


def setup(bot):
    bot.add_cog(PostQuotedTweet(bot))
