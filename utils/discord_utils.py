import re

from discord.ext import commands
from discord.utils import escape_mentions


def filter_nsfw(message: str):
    return re.sub(r'<.*>', '', message)


def filter_spoiler(message: str):
    return re.sub(r'\|\|[^\|]+\|\|', '', message)


def filter_commands(message: str):
    if message[0:2] == '!!':
        return ''

    return message


def clean_message(message: str, modules=None):
    if modules is None:
        modules = [filter_spoiler, filter_nsfw, filter_commands]

    ret = escape_mentions(message)

    for module in modules:
        ret = module(ret)

    return ret


def is_owner_check(message):
    return message.author.id == 287519043680862208


def is_owner():
    return commands.check(lambda ctx: is_owner_check(ctx.message))

