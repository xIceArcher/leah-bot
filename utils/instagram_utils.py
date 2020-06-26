import json
from datetime import datetime

import bs4
import requests

INSTAGRAM_PROXY_URL = 'https://instagram.com/tv/'

def get_insta_post(insta_post_id: str):
    request_url = INSTAGRAM_PROXY_URL + insta_post_id
    return json.loads(requests.get(request_url).content)

def get_insta_post_url(insta_post_id: str):
    return f'https://instagram.com/p/{insta_post_id}'

def get_insta_user_url(post: dict):
    return f'https://instagram.com/{extract_username(post)}'

def is_video(post: dict):
    return post['is_video']

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

def extract_video(post: dict):
    if is_video(post):
        return post['video_url']
    else:
        return None

def extract_text(post: dict, max_length: int):
    text = post['edge_media_to_caption']['edges'][0]['node']['text']
    return text[:max_length] + ('...' if len(text) > max_length else '')

def extract_likes(post: dict):
    return post['edge_media_preview_like']['count']

def extract_timestamp(post: dict):
    return datetime.utcfromtimestamp(int(post['taken_at_timestamp']))

