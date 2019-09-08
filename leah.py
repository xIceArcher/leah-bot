import logging

from discord.ext import commands

from utils.credentials_utils import get_credentials

logging.basicConfig(level=logging.INFO)

active_extensions = ['cogs.PostTweetMedia', 'cogs.PostRetweet', 'cogs.TwitterStalker']


def main():
    bot = commands.Bot(command_prefix='!!', description='placeholder')

    for extension in active_extensions:
        bot.load_extension(extension)

    credentials = get_credentials('credentials.json')
    bot.run(credentials['discord']['token'])


if __name__ == '__main__':
    main()
