import asyncio
import logging
from queue import Queue

import tweepy
from discord.ext import commands

from utils.twitter_utils import get_tweet_url, get_tweepy, get_user, extract_text
from utils.discord_utils import is_owner

logger = logging.getLogger(__name__)


class DiscordRepostListener(tweepy.StreamListener):
    def __init__(self, tweet_queue):
        super().__init__()
        self.tweet_queue = tweet_queue

    def on_status(self, tweet):
        self.tweet_queue.put(tweet)


class TwitterStalker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tweet_queue = Queue()
        self.listener = None
        self.stream = None
        self.stalk_ids = []
        self.stalk_destinations = {}

        self.start_stream()
        asyncio.run_coroutine_threadsafe(self.discord_poster(), bot.loop)

    def cog_unload(self):
        self.kill_stream()

    def start_stream(self):
        self.listener = DiscordRepostListener(tweet_queue=self.tweet_queue)
        self.stream = tweepy.Stream(auth=get_tweepy().auth, listener=self.listener)
        self.stream.filter(follow=self.stalk_ids, is_async=True)
        logger.info(f'Stream started! Now stalking IDs: {self.stalk_ids}')

    def kill_stream(self):
        self.listener = None
        self.stream.disconnect()
        self.stream = None
        logger.info('Stream killed!')

    def restart_stream(self):
        self.kill_stream()
        self.start_stream()

    @commands.command()
    @is_owner()
    async def stalk(self, ctx, screen_name: str):
        user = get_user(screen_name=screen_name)

        if not user:
            await ctx.channel.send(f'{screen_name} is not a valid Twitter username!')

        user_id = str(user.id)

        if user_id not in self.stalk_ids:
            self.stalk_ids.append(user_id)
            self.stalk_destinations[user_id] = []
            self.restart_stream()

        if ctx.channel.id not in self.stalk_destinations[user_id]:
            self.stalk_destinations[user_id].append(ctx.channel.id)
            await ctx.channel.send(f'Stalked {screen_name} (ID: {user_id}) in this channel!')
        else:
            await ctx.channel.send(f'{screen_name} (ID: {user_id}) is already being stalked in this channel!')

    @commands.command()
    @is_owner()
    async def unstalk(self, ctx, screen_name):
        user = get_user(screen_name=screen_name)

        if not user:
            await ctx.channel.send(f'{screen_name} is not a valid Twitter username!')

        user_id = str(user.id)

        if user_id not in self.stalk_ids or ctx.channel.id not in self.stalk_destinations[user_id]:
            await ctx.channel.send(f'{screen_name} (ID: {user_id}) is not being stalked in this channel!')

        self.stalk_destinations[user_id].remove(ctx.channel.id)

        if len(self.stalk_destinations[user_id]) == 0:
            self.stalk_ids.remove(user_id)
            del self.stalk_destinations[user_id]
            self.restart_stream()

        await ctx.channel.send(f'Unstalked {screen_name} (ID: {user_id}) in this channel!')

    @commands.command()
    @is_owner()
    async def stalks(self, ctx):
        stalked_users = []

        for user_id in self.stalk_destinations:
            if ctx.channel.id in self.stalk_destinations[user_id]:
                stalked_users.append(f'@{get_user(user_id=user_id).screen_name}')

        await ctx.channel.send(f'Users stalked in this channel: {", ".join(stalked_users)}')

    async def discord_poster(self):
        await self.bot.wait_until_ready()

        while True:
            if not self.tweet_queue.empty():
                tweet = self.tweet_queue.get()
                user_id = str(tweet.user.id)

                if user_id not in self.stalk_ids:
                    continue

                for channel_id in self.stalk_destinations[user_id]:
                    channel = self.bot.get_channel(channel_id)
                    await channel.send(get_tweet_url(tweet))
                    logger.info(f'{get_tweet_url(tweet)} sent to channel {channel_id}')

            else:
                await asyncio.sleep(1)


def setup(bot):
    bot.add_cog(TwitterStalker(bot))

