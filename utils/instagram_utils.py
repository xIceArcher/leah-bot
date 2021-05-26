from datetime import datetime

import aiohttp
import requests

INSTAGRAM_POST_PROXY_URL = 'https://instagram.com/tv/'
INSTAGRAM_TIMELINE_PROXY_URL = 'https://instagram.com/tv/'

MAX_RETRIES = 5

async def get_insta_post(shortcode: str):
    curr_retries = 0
    request_url = INSTAGRAM_POST_PROXY_URL + shortcode

    while curr_retries < MAX_RETRIES:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(request_url) as resp:
                    ret = await resp.json()
                    return ret["entry_data"]["PostPage"][0]["graphql"]["shortcode_media"]
        except requests.exceptions.Timeout:
            curr_retries += 1

def get_insta_timeline(username: str):
    curr_retries = 0
    request_url = INSTAGRAM_TIMELINE_PROXY_URL + username

    while curr_retries < MAX_RETRIES:
        try:
            return requests.get(request_url, timeout=5).json()
        except requests.exceptions.Timeout:
            curr_retries += 1

def get_insta_post_url(shortcode: str):
    return f'https://instagram.com/p/{shortcode}'

def get_insta_user_url(post: dict):
    return f'https://instagram.com/{extract_username(post)}'

def extract_username(user: dict):
    return user['username']

def extract_profile_pic_url(user: dict):
    return user['profile_pic_url']

def extract_full_name(user: dict):
    return user['full_name']

def extract_photos(post: dict):
    photos = None

    try:
        edges = post['edge_sidecar_to_children']['edges']
        photos = [edge['node']['display_url'] for edge in edges if not edge['node']['is_video']]
    except KeyError:
        # Post only has one image
        pass

    if not photos:
        photos = [post['display_url']]

    return photos

def extract_videos(post: dict):
    try:
        edges = post['edge_sidecar_to_children']['edges']
        return [edge['node']['video_url'] for edge in edges if edge['node']['is_video']]
    except KeyError:
        # Post is either a single image or a single video
        if post['is_video']:
            return [post['video_url']]
        else:
            return None

def extract_text(post: dict, max_length: int):
    try:
        text = post['edge_media_to_caption']['edges'][0]['node']['text']
        return text[:max_length] + ('...' if len(text) > max_length else '')
    except IndexError:
        return ''

def extract_likes(post: dict):
    return post['edge_media_preview_like']['count']

def extract_timestamp(post: dict):
    return datetime.utcfromtimestamp(int(post['taken_at_timestamp']))

def extract_post_count(timeline: dict):
    return timeline['edge_owner_to_timeline_media']['count']

def extract_recent_posts(timeline: dict, max_posts=12):
    # API only returns most recent 12 posts
    if max_posts > 12:
        max_posts = 12

    posts = timeline['edge_owner_to_timeline_media']['edges']
    ret = [post['node'] for post in posts][:max_posts]

    return ret
