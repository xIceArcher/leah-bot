import http
import re
from collections import OrderedDict

import requests
from urllib3.exceptions import InsecureRequestWarning
from urllib.parse import urljoin

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

def get_tweet_ids(s: str):
    regex = re.compile(r'(?:http[s]?://)?twitter\.com/[^/]*/status/([0-9]*)(?:\?[^ \r\n]*)?')
    return list(OrderedDict.fromkeys(regex.findall(s)))


def get_photo_id(url: str):
    return url[url.rfind('/') + 1: url.rfind('?')]


def get_photo_url(url: str, size='orig'):
    extension = url[url.rfind('.') + 1:]
    base = url[:url.rfind('.')]

    return f'{base}?format={extension}&name={size}'


def get_insta_shortcodes(s: str):
    ret = []

    regex = re.compile(r'http[s]?://(?:w{3}\.)?instagram\.com/p/([A-Za-z0-9\-_]*)/?(?:\?[^ \r\n]*)?')
    ret.extend(regex.findall(s))

    regex2 = re.compile(r'http[s]?://(?:w{3}\.)?instagram\.com/tv/([A-Za-z0-9\-_]*)/?(?:\?[^ \r\n]*)?')
    ret.extend(regex2.findall(s))

    return list(OrderedDict.fromkeys(ret))


def has_insta_links(s: str) -> bool:
    return re.compile(r'http[s]?://(?:w{3}\.)?instagram\.com').search(s) != None


def get_ameblo_links(s: str):
    regex = re.compile(r'http[s]?://ameblo\.jp/[A-Za-z0-9_\-]+/entry-[0-9]+\.html')
    return list(OrderedDict.fromkeys(regex.findall(s)))


def get_youtube_video_ids(s: str):
    ret = []

    regex = re.compile(r'(?:http[s]?://)(?:w{3}\.)?youtube\.com/watch\?v=([A-Za-z0-9_\-]+)')
    ret.extend(regex.findall(s))

    regex2 = re.compile(r'(?:http[s]?://)?(?:w{3}\.)?youtu\.be/([A-Za-z0-9_\-]+)')
    ret.extend(regex2.findall(s))

    return list(OrderedDict.fromkeys(ret))

def unpack_short_link(s: str):
    MAX_REDIRECTS = 5
    curr_redirects = 0

    prev_url = s
    while curr_redirects < MAX_REDIRECTS:
        try:
            res = requests.get(s, allow_redirects=False, verify=False)
        except requests.exceptions.MissingSchema:
            # Occurs when URL is relative
            try:
                s = urljoin(prev_url, s)
                res = requests.get(s, allow_redirects=False, verify=False)
            except Exception:
                break

        if not has_insta_links(s) and (res.status_code == http.HTTPStatus.MOVED_PERMANENTLY or res.status_code == http.HTTPStatus.FOUND):
            prev_url = s
            s = res.headers['Location']
            curr_redirects += 1
        else:
            break

    return s
