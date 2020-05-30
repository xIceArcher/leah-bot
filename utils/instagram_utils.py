import json

import bs4
import requests


def get_insta_post_info(url: str):
    soup = bs4.BeautifulSoup(requests.get(url).content, 'html.parser')

    raw_text = soup.body.script.string.strip()

    # Get rid of 'window._sharedData =' at front and ';' at back
    start = raw_text.find('=')
    end = raw_text.rfind(';')

    js = json.loads(raw_text[start + 1:end])

    ret = dict()

    # User
    owner_field = js['entry_data']['PostPage'][0]['graphql']['shortcode_media']['owner']
    ret['username'] = owner_field['username']
    ret['profile_pic_url'] = owner_field['profile_pic_url']
    ret['full_name'] = owner_field['full_name']

    # Photos
    try:
        edges = js['entry_data']['PostPage'][0]['graphql']['shortcode_media']['edge_sidecar_to_children']['edges']
        ret['photos'] = [edge['node']['display_url'] for edge in edges]
    except KeyError:
        # Post only has one image
        ret['photos'] = [js['entry_data']['PostPage'][0]['graphql']['shortcode_media']['display_url']]

    ret['text'] = js['entry_data']['PostPage'][0]['graphql']['shortcode_media']['edge_media_to_caption']['edges'][0]['node']['text']
    ret['url'] = url
    return ret
