import logging

from discord.ext import commands

from utils.credentials_utils import get_credentials

formatter = '%(levelname)s %(name)s:%(lineno)d: %(asctime)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=formatter)

active_extensions = ['cogs.Admin', 'cogs.PostQuotedTweet', 'cogs.PostTweetMedia', 'cogs.TwitterStalker', 'cogs.PostTime',
                     'cogs.PostInstaMedia', 'cogs.PostAmebloMedia', 'cogs.TwitterIconStalker', 'cogs.PostYoutubeInfo', 'cogs.InstaStalker']


def main():
    bot = commands.Bot(command_prefix='!!', description='placeholder')

    for extension in active_extensions:
        bot.load_extension(extension)

    credentials = get_credentials('credentials.json')
    bot.run(credentials['discord']['token'])


if __name__ == '__main__':
    main()
