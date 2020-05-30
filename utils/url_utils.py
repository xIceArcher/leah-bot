import http
import re
from collections import OrderedDict

import requests


def get_tweet_ids(s: str):
    regex = re.compile(r'(?:http[s]?://)?twitter\.com/[^/]*/status/([0-9]*)(?:\?[^ \r\n]*)?')
    return list(OrderedDict.fromkeys(regex.findall(s)))


def get_photo_id(url: str):
    return url[url.rfind('/') + 1: url.rfind('?')]


def get_photo_url(url: str, size='orig'):
    extension = url[url.rfind('.') + 1:]
    base = url[:url.rfind('.')]

    return f'{base}?format={extension}&name={size}'


def get_insta_links(s: str):
    regex = re.compile(r'http[s]?://(?:w{3}\.)?instagram\.com/(?:tv|p)/([A-Za-z0-9\-_]*)/?(?:\?[^ \r\n]*)?')
    return [f'https://www.instagram.com/tv/{id}/' for id in list(OrderedDict.fromkeys(regex.findall(s)))]


def get_ameblo_links(s: str):
    regex = re.compile(r'http[s]?://ameblo\.jp/[A-Za-z0-9_\-]+/entry-[0-9]+\.html')
    return list(OrderedDict.fromkeys(regex.findall(s)))


def unpack_short_link(s: str):
    MAX_REDIRECTS = 5
    curr_redirects = 0

    while curr_redirects < MAX_REDIRECTS:
        res = requests.get(s, allow_redirects=False)
        if res.status_code == http.HTTPStatus.MOVED_PERMANENTLY or res.status_code == http.HTTPStatus.FOUND:
            s = res.headers['Location']
            curr_redirects += 1
        else:
            break

    return s
