import re
from collections import OrderedDict


def get_tweet_ids(s: str):
    regex = re.compile(r'(?:http[s]?://)?twitter.com/[^/]*/status/([0-9]*)(?:\?[^ \r\n]*)?')
    return list(OrderedDict.fromkeys(regex.findall(s)))


def get_photo_id(url: str):
    return url[url.rfind('/') + 1: url.rfind('?')]


def get_photo_url(url: str, size='orig'):
    extension = url[url.rfind('.') + 1:]
    base = url[:url.rfind('.')]

    return f'{base}?format={extension}&name={size}'
