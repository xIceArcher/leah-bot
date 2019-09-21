import asyncio
import json
import logging
import os
from queue import Queue
from threading import Event, Thread

import tweepy
from aiohttp import ClientConnectorError
from discord.ext import commands
from tweepy import TweepError

from utils.discord_embed_utils import get_tweet_embeds, get_color_embed
from utils.twitter_utils import get_tweet_url, get_tweepy, get_user, extract_video_url, is_reply, get_tweet

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
        logger.info(f'Stream disconnected. Notice: {notice}')
        self.restart_flag.set()


class TwitterStalker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tweet_queue = Queue()
        self.restart_flag = Event()
        self.listener = None
        self.stream = None
        self.stream_thread = None
        self.stalk_destinations = {}
        self.stalk_users = {}
        self.colors = {}

        self.load_destinations()
        self.load_colors()
        self.setup_stalked_users()

        self.start_stream()
        asyncio.run_coroutine_threadsafe(self.discord_poster(), bot.loop)
        asyncio.run_coroutine_threadsafe(self.stream_restarter(), bot.loop)

    @commands.command()
    @commands.is_owner()
    async def stalk(self, ctx, screen_name: str):
        user = get_user(screen_name=screen_name)

        if not user:
            await ctx.channel.send(f'{screen_name} is not a valid Twitter username!')
            return

        user_id = user.id_str

        if user_id not in self.stalk_destinations:
            self.stalk_destinations[user_id] = []
            self.restart_flag.set()

        if ctx.channel.id not in self.stalk_destinations[user_id]:
            self.stalk_destinations[user_id].append(ctx.channel.id)
            await ctx.channel.send(f'Stalked {screen_name} (ID: {user_id}) in this channel!')
        else:
            await ctx.channel.send(f'{screen_name} (ID: {user_id}) is already being stalked in this channel!')
            return

        if ctx.channel.id not in self.stalk_users:
            self.stalk_users[ctx.channel.id] = []

        self.stalk_users[ctx.channel.id].append(user_id)

    @commands.command()
    @commands.is_owner()
    async def unstalk(self, ctx, screen_name):
        user = get_user(screen_name=screen_name)

        if not user:
            await ctx.channel.send(f'{screen_name} is not a valid Twitter username!')
            return

        user_id = user.id_str

        if user_id not in self.stalk_destinations or ctx.channel.id not in self.stalk_destinations[user_id]:
            await ctx.channel.send(f'{screen_name} (ID: {user_id}) is not being stalked in this channel!')
            return

        self.stalk_destinations[user_id].remove(ctx.channel.id)

        if not self.stalk_destinations[user_id]:
            del self.stalk_destinations[user_id]
            self.restart_flag.set()

        await ctx.channel.send(f'Unstalked {screen_name} (ID: {user_id}) in this channel!')

        self.stalk_users[ctx.channel.id].remove(user_id)

        if not self.stalk_users[ctx.channel.id]:
            del self.stalk_users[ctx.channel.id]

    @commands.command()
    async def stalks(self, ctx):
        stalk_names = [f'@{get_user(user_id=user_id).screen_name}' for user_id in self.stalk_users[ctx.channel.id]]
        await ctx.channel.send(f'Users stalked in this channel: {", ".join(stalk_names)}')

    @commands.command()
    @commands.is_owner()
    async def embed(self, ctx, tweet_id: int):
        for embed in get_tweet_embeds(get_tweet(tweet_id=tweet_id)):
            await ctx.channel.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def restart(self, ctx):
        self.restart_flag.set()
        await ctx.channel.send('Restart flag set!')

    @commands.command()
    @commands.is_owner()
    async def color(self, ctx, screen_name: str, hex_code: str = None):
        user = get_user(screen_name=screen_name)

        if not hex_code:
            user_color = self.colors.get(user.id_str)

            if user_color:
                await ctx.channel.send(embed=get_color_embed(
                    message=f'User @{screen_name} (ID: {user.id_str}) has color {hex(user_color)}',
                    color=user_color))
            else:
                await ctx.channel.send(f'User @{screen_name} (ID: {user.id_str}) has no color')
        else:
            try:
                user_color = int(hex_code, 16)
            except ValueError:
                await ctx.channel.send('Invalid hex code!')
                return

            self.colors[user.id_str] = user_color
            self.save_colors()

            await ctx.channel.send(embed=get_color_embed(
                message=f'User @{screen_name} (ID: {user.id_str}) now has color {hex(user_color)}',
                color=user_color))

    async def discord_poster(self):
        await self.bot.wait_until_ready()

        while True:
            if not self.tweet_queue.empty():
                short_tweet = self.tweet_queue.get()
                user_id = short_tweet.user.id_str

                if user_id not in self.stalk_destinations:
                    continue

                try:
                    try:
                        extended_tweet = get_tweet(short_tweet.id)
                    except TweepError as e:
                        self.tweet_queue.put(short_tweet)
                        logger.info(f'Tweepy error occured: {e}, sleeping for 30 seconds...')
                        await asyncio.sleep(30)
                        continue

                    embeds = get_tweet_embeds(extended_tweet, color=self.colors.get(short_tweet.user.id_str))
                    video = extract_video_url(extended_tweet)

                    for channel_id in self.stalk_destinations[user_id]:
                        if is_reply(extended_tweet) and extended_tweet.in_reply_to_user_id_str not in self.stalk_users[
                            channel_id]:
                            continue

                        channel = self.bot.get_channel(channel_id)

                        try:
                            for embed in embeds:
                                await channel.send(embed=embed)

                            if video:
                                await channel.send(video)
                        except ClientConnectorError:
                            self.tweet_queue.put(short_tweet)
                            logger.info(f'Could not connect to client, requeueing tweet {short_tweet.id}')
                            break

                        logger.info(
                            f'{get_tweet_url(extended_tweet)} sent to channel {self.bot.get_channel(channel_id).name}'
                            f' in {self.bot.get_channel(channel_id).guild.name}')
                except Exception as e:
                    logger.exception(e)
            else:
                await asyncio.sleep(1)

    async def stream_restarter(self):
        while True:
            if self.restart_flag.is_set():
                logger.info('Restarting stream......')
                self.kill_stream()
                self.start_stream()
                self.save_destinations()
                self.restart_flag.clear()
                logger.info('Stream restarted!')

            await asyncio.sleep(60)

    def start_stream(self):
        self.listener = DiscordRepostListener(tweet_queue=self.tweet_queue, restart_flag=self.restart_flag)
        self.stream = tweepy.Stream(auth=get_tweepy().auth, listener=self.listener)
        self.stream_thread = Thread(target=self.start_stream_thread)
        self.stream_thread.start()
        logger.info(f'Stream started! Now stalking IDs: {list(self.stalk_destinations)}')

    def start_stream_thread(self):
        try:
            self.stream.filter(follow=list(self.stalk_destinations))
        except Exception as e:
            logger.info('Stream crashed')
            logger.exception(e)
        finally:
            self.restart_flag.set()
            logger.info('Stream terminated, awaiting restart...')

    def kill_stream(self):
        self.listener = None

        if self.stream:
            self.stream.disconnect()
        self.stream_thread.join()

        self.stream = None
        logger.info('Stream killed!')

    def restart_stream(self):
        self.kill_stream()
        self.start_stream()

    def load_destinations(self):
        path = os.path.join(os.getcwd(), 'data', 'tweets.json')
        with open(path) as f:
            self.stalk_destinations = json.load(f)

    def load_colors(self):
        path = os.path.join(os.getcwd(), 'data', 'colors.json')
        with open(path) as f:
            self.colors = json.load(f)

    def save_destinations(self):
        path = os.path.join(os.getcwd(), 'data', 'tweets.json')
        with open(path, 'w') as f:
            f.seek(0)
            json.dump(self.stalk_destinations, f, indent=4)

    def save_colors(self):
        path = os.path.join(os.getcwd(), 'data', 'colors.json')
        with open(path, 'w') as f:
            f.seek(0)
            json.dump(self.colors, f, indent=4)

    def setup_stalked_users(self):
        for user_id in self.stalk_destinations:
            for channel_id in self.stalk_destinations[user_id]:
                if channel_id not in self.stalk_users:
                    self.stalk_users[channel_id] = []

                self.stalk_users[channel_id].append(user_id)

    def cog_unload(self):
        self.kill_stream()


def setup(bot):
    bot.add_cog(TwitterStalker(bot))
