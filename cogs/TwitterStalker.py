import json
import logging
import os
from datetime import datetime, timezone
from queue import Queue
from threading import Event, Thread

import tweepy
from aiohttp import ClientConnectorError
from discord.ext import commands, tasks
from tweepy import TweepError

from utils.discord_embed_utils import get_tweet_embeds, get_color_embed
from utils.twitter_utils import get_tweet_url, get_tweepy, get_user, is_reply, get_tweet, \
    extract_displayed_video_url, get_timeline, get_mock_tweet, is_retweet
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

    @tasks.loop(seconds=1.0)
    async def discord_poster(self):
        if not self.tweet_queue.empty():
            short_tweet = self.tweet_queue.get()
            user_id = short_tweet.user.id_str

            if user_id not in self.stalk_destinations:
                return

            try:
                extended_tweet = get_tweet(short_tweet.id)
            except TweepError as e:
                self.handle_posting_error(error_tweet=short_tweet)
                return

            if is_retweet(extended_tweet) and extended_tweet.retweeted_status.id in self.tweet_history:
                await self.handle_posted_retweet(extended_tweet)
            else:
                await self.handle_new_tweet(extended_tweet)

    async def handle_new_tweet(self, tweet):
        user_id = tweet.user.id_str

        embeds = get_tweet_embeds(tweet, color=self.colors.get(user_id))

        if is_retweet(tweet):
            self.tweet_history[tweet.retweeted_status.id] = []
        else:
            self.tweet_history[tweet.id] = []

        for channel_id in self.stalk_destinations[user_id]:
            if not self.is_relevant(tweet, channel_id):
                continue

            channel = self.bot.get_channel(channel_id)
            video_url = extract_displayed_video_url(tweet)

            try:
                main_discord_message = await channel.send(embed=embeds[0])
                for embed in embeds[1:]:
                    await channel.send(embed=embed)

                if video_url:
                    await channel.send(video_url)

                if is_retweet(tweet):
                    self.tweet_history[tweet.retweeted_status.id].append((channel_id, main_discord_message.id))
                else:
                    self.tweet_history[tweet.id].append((channel_id, main_discord_message.id))
            except ClientConnectorError:
                self.tweet_queue.put(tweet)
                logger.info(f'Could not connect to client, requeueing tweet {tweet.id}')
                break

            self.last_tweet_time = datetime.now(timezone.utc)
            logger.info(
                f'{get_tweet_url(tweet)} sent to channel {self.bot.get_channel(channel_id).name}'
                f' in {self.bot.get_channel(channel_id).guild.name}')

    def is_relevant(self, tweet, channel_id):
        return not is_reply(tweet) or tweet.in_reply_to_user_id_str in self.stalk_users[channel_id]

    async def handle_posted_retweet(self, tweet):
        RETWEETED_BY_FIELD_NAME = 'Retweeted by'

        td = tweet.created_at - tweet.retweeted_status.created_at
        str_appended = f'[@{tweet.user.name}]({get_tweet_url(tweet=tweet)}) ({format_time_delta(td)} later)'

        for channel_id, message_id in self.tweet_history[tweet.retweeted_status.id]:
            channel = self.bot.get_channel(channel_id)
            message = await channel.fetch_message(message_id)
            found_flag = False

            original_embed = message.embeds[0]
            new_embed = original_embed

            for i in range(len(original_embed.fields)):
                original_field = original_embed.fields[i]

                if original_field.name == RETWEETED_BY_FIELD_NAME:
                    found_flag = True
                    new_embed.set_field_at(i, name=RETWEETED_BY_FIELD_NAME,
                                           value=f'{original_field.value}\n {str_appended}', inline=False)

            if not found_flag:
                new_embed.add_field(name=RETWEETED_BY_FIELD_NAME, value=str_appended, inline=False)

            await message.edit(embed=new_embed)
            logger.info(
                f'{get_tweet_url(tweet)} sent to channel {self.bot.get_channel(channel_id).name} in {self.bot.get_channel(channel_id).guild.name}')

    def handle_posting_error(self, error_tweet):
        if hasattr(error_tweet, 'curr_retries'):
            if error_tweet.curr_retries > 5:
                logger.info(
                    f'Failed to post tweet {error_tweet.id} from user {get_user(user_id=error_tweet.user.id).name}')
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
        self.discord_poster.cancel()
        self.stream_restarter.cancel()
        self.save_destinations()

    @discord_poster.before_loop
    @stream_restarter.before_loop
    async def await_ready(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(TwitterStalker(bot))
