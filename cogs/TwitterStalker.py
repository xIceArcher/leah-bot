import asyncio
import json
import logging
import os
from queue import Queue
from threading import Event

import tweepy
from discord.ext import commands

from utils.discord_embed_utils import get_tweet_embeds
from utils.twitter_utils import get_tweet_url, get_tweepy, get_user, is_retweet, is_reply, extract_video_url

logger = logging.getLogger(__name__)


class DiscordRepostListener(tweepy.StreamListener):
    def __init__(self, tweet_queue, restart_flag):
        super().__init__()
        self.tweet_queue = tweet_queue
        self.restart_flag = restart_flag

    def on_connect(self):
        logger.info('Stream connected')

    def on_status(self, tweet):
        self.tweet_queue.put(tweet)

    def on_error(self, status_code):
        logger.info(f'Stream error. Status code: {status_code}')
        self.restart_flag.set()

    def on_timeout(self):
        logger.info('Stream timeout')
        self.restart_flag.set()

    def on_disconnect(self, notice):
        logger.info(f'Stream crashed. Notice: {notice}')
        self.restart_flag.set()


class TwitterStalker(commands.Cog):
    def __init__(self, bot, retweet_flag=False, reply_flag=False):
        self.bot = bot
        self.retweet_flag = retweet_flag
        self.reply_flag = reply_flag
        self.tweet_queue = Queue()
        self.restart_flag = Event()
        self.listener = None
        self.stream = None
        self.stalk_destinations = {}
        self.colors = {}

        self.load_json()

        self.start_stream()
        asyncio.run_coroutine_threadsafe(self.discord_poster(), bot.loop)
        asyncio.run_coroutine_threadsafe(self.stream_restarter(), bot.loop)

    @commands.command()
    @commands.is_owner()
    async def stalk(self, ctx, screen_name: str):
        user = get_user(screen_name=screen_name)

        if not user:
            await ctx.channel.send(f'{screen_name} is not a valid Twitter username!')

        user_id = str(user.id)

        if user_id not in self.stalk_destinations:
            self.stalk_destinations[user_id] = []
            self.restart_flag.set()

        if ctx.channel.id not in self.stalk_destinations[user_id]:
            self.stalk_destinations[user_id].append(ctx.channel.id)
            await ctx.channel.send(f'Stalked {screen_name} (ID: {user_id}) in this channel!')
        else:
            await ctx.channel.send(f'{screen_name} (ID: {user_id}) is already being stalked in this channel!')

    @commands.command()
    @commands.is_owner()
    async def unstalk(self, ctx, screen_name):
        user = get_user(screen_name=screen_name)

        if not user:
            await ctx.channel.send(f'{screen_name} is not a valid Twitter username!')

        user_id = str(user.id)

        if user_id not in self.stalk_destinations or ctx.channel.id not in self.stalk_destinations[user_id]:
            await ctx.channel.send(f'{screen_name} (ID: {user_id}) is not being stalked in this channel!')

        self.stalk_destinations[user_id].remove(ctx.channel.id)

        if len(self.stalk_destinations[user_id]) == 0:
            del self.stalk_destinations[user_id]
            self.restart_flag.set()

        await ctx.channel.send(f'Unstalked {screen_name} (ID: {user_id}) in this channel!')

    @commands.command()
    async def stalks(self, ctx):
        stalked_users = []

        for user_id in self.stalk_destinations:
            if ctx.channel.id in self.stalk_destinations[user_id]:
                stalked_users.append(f'@{get_user(user_id=user_id).screen_name}')

        await ctx.channel.send(f'Users stalked in this channel: {", ".join(stalked_users)}')

    @commands.command()
    @commands.is_owner()
    async def embed(self, ctx, tweet_id: int):
        for embed in get_tweet_embeds(tweet_id=tweet_id):
            await ctx.channel.send(embed=embed)

    async def discord_poster(self):
        await self.bot.wait_until_ready()

        while True:
            if not self.tweet_queue.empty():
                tweet = self.tweet_queue.get()

                if is_retweet(tweet) and not self.retweet_flag:
                    continue

                if is_reply(tweet, user_id_whitelist=list(self.stalk_destinations)) and not self.reply_flag:
                    continue

                user_id = tweet.user.id_str

                if user_id not in self.stalk_destinations:
                    continue

                for channel_id in self.stalk_destinations[user_id]:
                    channel = self.bot.get_channel(channel_id)

                    for embed in get_tweet_embeds(tweet_id=tweet.id, color=self.colors.get(tweet.user.id_str)):
                        await channel.send(embed=embed)

                    video = extract_video_url(tweet)

                    if video:
                        await channel.send(video)

                    logger.info(f'{get_tweet_url(tweet)} sent to channel {self.bot.get_channel(channel_id).name}'
                                f' in {self.bot.get_channel(channel_id).guild.name}')

            else:
                await asyncio.sleep(1)

    async def stream_restarter(self):
        while True:
            if self.restart_flag.is_set():
                self.kill_stream()
                self.start_stream()
                self.save_json()
                self.restart_flag.clear()

            await asyncio.sleep(60)

    def start_stream(self):
        self.listener = DiscordRepostListener(tweet_queue=self.tweet_queue, restart_flag=self.restart_flag)
        self.stream = tweepy.Stream(auth=get_tweepy().auth, listener=self.listener)
        self.stream.filter(follow=list(self.stalk_destinations), is_async=True)
        logger.info(f'Stream started! Now stalking IDs: {list(self.stalk_destinations)}')

    def kill_stream(self):
        self.listener = None
        self.stream.disconnect()
        self.stream = None
        logger.info('Stream killed!')

    def restart_stream(self):
        self.kill_stream()
        self.start_stream()

    def load_json(self):
        stalk_path = os.path.join(os.getcwd(), 'data', 'tweets.json')
        with open(stalk_path) as f:
            self.stalk_destinations = json.load(f)

        colors_path = os.path.join(os.getcwd(), 'data', 'colors.json')
        with open(colors_path) as f:
            self.colors = json.load(f)

    def save_json(self):
        path = os.path.join(os.getcwd(), 'data', 'tweets.json')
        with open(path, 'w') as f:
            f.seek(0)
            json.dump(self.stalk_destinations, f, indent=4)

    def cog_unload(self):
        self.kill_stream()


def setup(bot):
    bot.add_cog(TwitterStalker(bot))
