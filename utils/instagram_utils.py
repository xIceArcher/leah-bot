import json

import bs4
import requests


def get_insta_photo_urls(url: str):
    soup = bs4.BeautifulSoup(requests.get(url).content, 'html.parser')

    raw_text = soup.body.script.text.strip()

    # Get rid of 'window._sharedData =' at front and ';' at back
    start = raw_text.find('=')
    end = raw_text.rfind(';')

    js = json.loads(raw_text[start + 1:end])

    try:
        edges = js['entry_data']['PostPage'][0]['graphql']['shortcode_media']['edge_sidecar_to_children']['edges']
        photo_urls = [edge['node']['display_url'] for edge in edges]
    except KeyError:
        # Post only has one image
        return []

    photo_urls.pop(0)
    return photo_urls
