import json
from datetime import datetime

import bs4
import requests


def get_insta_post(id: str):
    api_url = f'https://instagram.com/tv/{id}'
    soup = bs4.BeautifulSoup(requests.get(api_url).content, 'html.parser')

    raw_text = soup.body.script.string.strip()

    # Get rid of 'window._sharedData =' at front and ';' at back
    start = raw_text.find('=')
    end = raw_text.rfind(';')

    js = json.loads(raw_text[start + 1:end])
    return js['entry_data']['PostPage'][0]['graphql']['shortcode_media']

def get_insta_post_url(id: str):
    return f'https://instagram.com/p/{id}'

def get_insta_user_url(post: dict):
    return f'https://instagram.com/{extract_username(post)}'

def extract_username(post: dict):
    return post['owner']['username']

def extract_profile_pic_url(post: dict):
    return post['owner']['profile_pic_url']

def extract_full_name(post: dict):
    return post['owner']['full_name']

def extract_photos(post: dict):
    try:
        edges = post['edge_sidecar_to_children']['edges']
        return [edge['node']['display_url'] for edge in edges]
    except KeyError:
        # Post only has one image
        return [post['display_url']]

def extract_text(post: dict, max_length: int):
    text = post['edge_media_to_caption']['edges'][0]['node']['text']
    return text[:max_length] + ('...' if len(text) > max_length else '')

def extract_likes(post: dict):
    return post['edge_media_preview_like']['count']

def extract_timestamp(post: dict):
    return datetime.utcfromtimestamp(int(post['taken_at_timestamp']))

