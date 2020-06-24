import googleapiclient.discovery

from utils.credentials_utils import get_credentials

youtube_api = None

API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'


def init_youtube(credentials_file='credentials.json'):
    global youtube_api

    credentials = get_credentials(credentials_file)

    youtube_api = googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, developerKey=credentials['google']['apiKey'])


def get_youtube():
    global youtube_api

    if not youtube_api:
        init_youtube()

    return youtube_api


def get_video(id: str, parts: list = None):
    api = get_youtube()

    if parts:
        parts_str = ','.join(parts) + ',snippet'
    else:
        parts_str = 'snippet'

    request = api.videos().list(part=parts_str,id=id)
    return request.execute()['items'][0]


def get_channel(id: str, parts: list = None):
    api = get_youtube()

    if parts:
        parts_str = ','.join(parts) + ',snippet'
    else:
        parts_str = 'snippet'

    request = api.channels().list(part=parts_str,id=id)
    return request.execute()['items'][0]


def get_video_url(id: str):
    return f'https://www.youtube.com/watch?v={id}'


def get_channel_url(id: str):
    return f'https://www.youtube.com/channel/{id}'


def is_livestream(video: dict):
    return video['snippet']['liveBroadcastContent'] != 'none'
