import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from math import ceil
from queue import Queue
from threading import Event, Thread

import discord
import tweepy
from aiohttp import ClientConnectorError
from discord.ext import commands, tasks
from tweepy import TweepError

from utils.discord_embed_twitter_utils import get_tweet_embeds, get_color_embed
from utils.twitter_utils import get_tweet_url, get_tweepy, get_user, is_reply, get_tweet, \
    extract_displayed_video_url, get_timeline, get_mock_tweet, extract_visible_id
from utils.url_utils import get_tweet_ids
from utils.utils import format_time_delta

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
        self.last_tweet_time = datetime.now(timezone.utc)
        self.tweet_history = {}

        self.load_destinations()
        self.load_colors()
        self.setup_stalked_users()

        self.start_stream()
        self.discord_poster.start()
        self.stream_restarter.start()

    @commands.command()
    @commands.is_owner()
    async def stalk(self, ctx, *args):
        time, screen_names = None, None

        if len(args) == 0:
            await TwitterStalker.stalks(self, ctx)
            return
        elif len(args) == 1:
            screen_names = [args[0]]
        else:
            try:
                time = int(args[-1])
                screen_names = args[0:-1]
            except ValueError:
                screen_names = args

        for screen_name in screen_names:
            user = get_user(screen_name=screen_name)

            if not user:
                await ctx.channel.send(f'@{screen_name} is not a valid Twitter username!')
                return

            user_id = user.id_str

            if user_id not in self.stalk_destinations:
                self.stalk_destinations[user_id] = []
                self.restart_flag.set()

            if ctx.channel.id not in self.stalk_destinations[user_id]:
                self.stalk_destinations[user_id].append(ctx.channel.id)
                if time:
                    logger.info(f'Stalked @{user.screen_name} in #{ctx.channel.name} in {ctx.guild.name} for {time} minutes')
                    await ctx.channel.send(f'Stalked @{user.screen_name} in this channel! Will auto-unstalk after {time} minutes.')
                else:
                    logger.info(f'Stalked @{user.screen_name} in #{ctx.channel.name} in {ctx.guild.name}')
                    await ctx.channel.send(f'Stalked @{user.screen_name} in this channel!')
            else:
                await ctx.channel.send(f'@{user.screen_name} is already being stalked in this channel!')
                return

            if ctx.channel.id not in self.stalk_users:
                self.stalk_users[ctx.channel.id] = []
                self.tweet_history[ctx.channel.id] = {}

            self.stalk_users[ctx.channel.id].append(user_id)

            if time:
                asyncio.run_coroutine_threadsafe(self.auto_unstalk(ctx, user.screen_name, time), self.bot.loop)

    @commands.command()
    @commands.is_owner()
    async def unstalk(self, ctx, screen_name):
        await self.do_unstalk(ctx, screen_name, timed=False)

    async def auto_unstalk(self, ctx, screen_name: str, time: int = None):
        await asyncio.sleep(time * 60)
        logger.info(f"Auto-unstalking @{screen_name} in #{ctx.channel.name} in {ctx.guild.name}")
        await self.do_unstalk(ctx, screen_name, timed=True)

    async def do_unstalk(self, ctx, screen_name: str, timed: bool):
        user = get_user(screen_name=screen_name)

        if not user:
            await ctx.channel.send(f'@{screen_name} is not a valid Twitter username!')
            return

        user_id = user.id_str

        if not timed and (
                user_id not in self.stalk_destinations or ctx.channel.id not in self.stalk_destinations[user_id]):
            await ctx.channel.send(f'@{user.screen_name} (ID: {user_id}) is not being stalked in this channel!')
            return

        self.stalk_destinations[user_id].remove(ctx.channel.id)

        if not self.stalk_destinations[user_id]:
            del self.stalk_destinations[user_id]
            self.restart_flag.set()

        logger.info(f'Unstalked @{user.screen_name} in #{ctx.channel.name} in {ctx.guild.name}')
        await ctx.channel.send(f'Unstalked @{user.screen_name} in this channel!')

        self.stalk_users[ctx.channel.id].remove(user_id)

        if not self.stalk_users[ctx.channel.id]:
            del self.stalk_users[ctx.channel.id]
            del self.tweet_history[ctx.channel.id]

    @commands.command()
    async def stalks(self, ctx):
        try:
            stalk_names = [f'@{get_user(user_id=user_id).screen_name}' for user_id in self.stalk_users[ctx.channel.id]]
        except KeyError:
            await ctx.channel.send('No users stalked in this channel!')
            return

        await ctx.channel.send(f'Users stalked in this channel: {", ".join(stalk_names)}')

    @commands.command()
    @commands.is_owner()
    async def queue(self, ctx, url: str):
        tweet_id = get_tweet_ids(url)[0]
        tweet = get_tweet(tweet_id)

        self.tweet_queue.put(get_mock_tweet(tweet.user.id, tweet_id))
        await ctx.channel.send(f'Queued tweet {tweet_id}!')

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

    @commands.command()
    @commands.is_owner()
    async def catchup(self, ctx, time=None):
        if time:
            time_arr = list(map(int, time.split(' ')))
            from_time = datetime(time_arr[0], time_arr[1], time_arr[2], time_arr[3], time_arr[4]).astimezone(
                timezone.utc)
        else:
            from_time = self.last_tweet_time

        tweets = []

        for user_id in self.stalk_destinations:
            for tweet in get_timeline(user_id):
                if tweet.created_at.astimezone(timezone.utc) > from_time:
                    tweets.append(get_mock_tweet(user_id, tweet.id, tweet.created_at))

        tweets.sort(key=lambda x: x.created_at)

        for tweet in tweets:
            self.tweet_queue.put(tweet)

        logger.info(f'Successfully caught up from {from_time}')

    @commands.command()
    async def archive(self, ctx, screen_name):
        if ctx.channel.id != 698491606151725056 and ctx.channel.id != 619909548492455937:
            logger.info(f'Illegal access from channel #{ctx.channel.name} in {ctx.guild.name}')
            return

        user = get_user(screen_name=screen_name)

        if not user:
            await ctx.channel.send(f'User @{screen_name} does not exist!')

        if user.protected:
            await ctx.channel.send(f'User @{screen_name} is protected!')
            return

        logger.info(f'Archiving @{screen_name}')
        if user.id in self.stalk_destinations and len(self.stalk_destinations[user.id_str]) > 1:
            logger.info("Aborting, user stalked in another channel")
            return

        if user.statuses_count > 3200:
            await ctx.channel.send(
                f'User @{screen_name} has {user.statuses_count} tweets, can only archive latest 3200.')

        tweets = []
        tweets_json = []
        num_tweets = min(3200, user.statuses_count)
        num_fetches = ceil(num_tweets / 200)

        max_id = None
        for _ in range(num_fetches):
            for tweet in get_timeline(user.id, 200, max_id):
                tweets.append(tweet)
                tweets_json.append(tweet._json)

            max_id = tweets[-1].id - 1
            await asyncio.sleep(10)

        temp_file_name = f'{screen_name}.json'

        with open(temp_file_name, 'w') as f:
            f.write(json.dumps(tweets_json, indent=4))

        await ctx.channel.send(file=discord.File(f'{screen_name}.json'))
        logger.info(f'Archiving @{screen_name} complete')
        os.remove(temp_file_name)

    @tasks.loop(seconds=1.0)
    async def discord_poster(self):
        while not self.tweet_queue.empty():
            short_tweet = self.tweet_queue.get()
            user_id = short_tweet.user.id_str

            if user_id not in self.stalk_destinations:
                continue

            try:
                extended_tweet = get_tweet(short_tweet.id)
            except TweepError:
                self.handle_posting_error(error_tweet=short_tweet)
                continue

            for channel_id in self.stalk_destinations[user_id]:
                if not self.is_relevant(extended_tweet, channel_id):
                    continue

                if extract_visible_id(extended_tweet) in self.tweet_history[channel_id]:
                    await self.handle_posted_retweet(extended_tweet, channel_id)
                else:
                    await self.handle_new_tweet(extended_tweet, channel_id)

    def is_relevant(self, tweet, channel_id):
        return not is_reply(tweet) or tweet.in_reply_to_user_id_str in self.stalk_users[channel_id]

    async def handle_new_tweet(self, tweet, channel_id):
        user_id = tweet.user.id_str
        embeds = get_tweet_embeds(tweet, color=self.colors.get(user_id))
        video_url = extract_displayed_video_url(tweet)

        channel = self.bot.get_channel(channel_id)

        try:
            main_discord_message = await channel.send(embed=embeds[0])

            if len(embeds) == 1:
                timestamp_discord_message = main_discord_message
            else:
                for embed in embeds[1:-1]:
                    await channel.send(embed=embed)
                timestamp_discord_message = await channel.send(embed=embeds[-1])

            if video_url:
                await channel.send(video_url)

            self.tweet_history[channel_id][extract_visible_id(tweet)] = (
            main_discord_message.id, timestamp_discord_message.id)
        except ClientConnectorError:
            self.tweet_queue.put(tweet)
            logger.info(f'Could not connect to client, requeueing tweet {tweet.id}')
            return

        self.last_tweet_time = datetime.now(timezone.utc)
        logger.info(f'{get_tweet_url(tweet)} sent to channel #{channel.name} in {channel.guild.name}')

    async def handle_posted_retweet(self, tweet, channel_id):
        RETWEETED_BY_FIELD_NAME = 'Retweeted by'

        channel = self.bot.get_channel(channel_id)
        main_message_id, timestamp_message_id = self.tweet_history[channel_id][extract_visible_id(tweet)]
        main_message = await channel.fetch_message(main_message_id)

        original_embed = main_message.embeds[0]
        new_embed = original_embed

        timestamp_message = await channel.fetch_message(timestamp_message_id)
        td = tweet.created_at - timestamp_message.embeds[0].timestamp
        str_appended = f'[@{tweet.user.name}]({get_tweet_url(tweet=tweet)}) ({format_time_delta(td)} later)'

        found_flag = False

        for i in range(len(original_embed.fields)):
            original_field = original_embed.fields[i]

            if original_field.name == RETWEETED_BY_FIELD_NAME:
                found_flag = True
                new_embed.set_field_at(i, name=RETWEETED_BY_FIELD_NAME,
                                       value=f'{original_field.value}\n{str_appended}', inline=False)

        if not found_flag:
            new_embed.add_field(name=RETWEETED_BY_FIELD_NAME, value=str_appended, inline=False)

        await main_message.edit(embed=new_embed)
        logger.info(f'Retweet {get_tweet_url(tweet)} sent to channel #{channel.name} in {channel.guild.name}')

    def handle_posting_error(self, error_tweet):
        if hasattr(error_tweet, 'curr_retries'):
            if error_tweet.curr_retries > 5:
                error_username = get_user(user_id=error_tweet.user.id).name
                logger.info(f'Failed to post tweet {error_tweet.id} from user {error_username}')
            else:
                error_tweet.curr_retries += 1
                self.tweet_queue.put(error_tweet)
        else:
            setattr(error_tweet, 'curr_retries', 1)
            self.tweet_queue.put(error_tweet)

    @tasks.loop(minutes=1.0)
    async def stream_restarter(self):
        if self.restart_flag.is_set():
            logger.info('Restarting stream......')
            self.kill_stream()
            self.start_stream()
            self.save_destinations()
            self.restart_flag.clear()
            logger.info('Stream restarted!')

    def start_stream(self):
        self.listener = DiscordRepostListener(tweet_queue=self.tweet_queue, restart_flag=self.restart_flag)
        self.stream = tweepy.Stream(auth=get_tweepy().auth, listener=self.listener)
        self.stream_thread = Thread(target=self.start_stream_thread)
        self.stream_thread.start()
        logger.info(f'Stream started! Now stalking IDs: {list(self.stalk_destinations)}')

    def start_stream_thread(self):
        try:
            self.stream.filter(follow=list(self.stalk_destinations))
        except:
            logger.info('Stream crashed')
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
                    self.tweet_history[channel_id] = {}

                self.stalk_users[channel_id].append(user_id)

    def cog_unload(self):
        self.kill_stream()
        self.discord_poster.cancel()
        self.stream_restarter.cancel()
        self.save_destinations()

    @discord_poster.before_loop
    @stream_restarter.before_loop
    async def await_ready(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(TwitterStalker(bot))
