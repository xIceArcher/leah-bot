import re

from discord.utils import escape_mentions


def filter_nsfw(message: str):
    return re.sub(r'<.*>', '', message)


def filter_spoiler(message: str):
    return re.sub(r'\|\|[^\|]+\|\|', '', message)


def clean_message(message: str, modules=None):
    if modules is None:
        modules = [filter_spoiler, filter_nsfw]

    ret = escape_mentions(message)

    for module in modules:
        ret = module(ret)

    return ret
