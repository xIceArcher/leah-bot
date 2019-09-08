import logging

from discord.ext import commands

from utils.discord_utils import clean_message
from utils.twitter_utils import extract_photos, get_tweet
from utils.url_utils import get_tweet_ids, get_photo_id

logger = logging.getLogger(__name__)

MAX_MEDIA_COUNT = 5


class PostTweetMedia(commands.Cog):
    @commands.Cog.listener()
    async def on_message(self, message):
        cleaned_message = clean_message(message.content)
        sent_media_count = 0

        for tweet_id in get_tweet_ids(cleaned_message):
            tweet = get_tweet(tweet_id)
            photos = extract_photos(tweet)

            logger.info(f'Message: {message.content}, Tweet ID: {tweet_id}, Photos: {photos}')

            if photos is None or len(photos) == 0:
                continue

            photos.pop(0)

            for photo in photos:
                if sent_media_count >= MAX_MEDIA_COUNT:
                    await message.channel.send('ツイートメディアは遊びじゃない！')
                    return

                if cleaned_message.find(get_photo_id(photo)) == -1:
                    sent_media_count += 1
                    await message.channel.send(photo)

    @commands.command()
    async def photos(self, ctx, twitter_url: str):
        tweet_ids = get_tweet_ids(twitter_url)

        if len(tweet_ids) == 0:
            await ctx.channel.send("Message does not contain a Twitter link!")
            return

        tweet = get_tweet(tweet_ids[0])
        photos = extract_photos(tweet)

        if len(photos) == 0:
            await ctx.channel.send("Tweet does not have any photos!")
            return

        logger.info(f'Twitter URL: {twitter_url}, Tweet ID: {tweet_ids[0]}, Photos: {photos}')

        for photo in photos:
            await ctx.channel.send(photo)


def setup(bot):
    bot.add_cog(PostTweetMedia())
