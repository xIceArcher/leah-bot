import requests
import bs4
import json

def get_line_live_m3u8_links(broadcast_link: str):
    LINE_LIVE_URL_TEMPLATE = 'https://lssapi.line-apps.com/v1/live/playInfo?contentId={}'

    soup = bs4.BeautifulSoup(requests.get(broadcast_link).content, 'html.parser')
    data_broadcast_json = soup.find('div').get('data-broadcast')
    if data_broadcast_json is None:
        return None

    try:
        lsa_path = json.loads(data_broadcast_json)['lsaPath']
    except KeyError:
        return None

    actual_link = LINE_LIVE_URL_TEMPLATE.format(lsa_path)
    m3u8_json = json.loads(requests.get(actual_link).content)

    try:
        play_urls = m3u8_json['playUrls']
    except KeyError:
        return None

    best_res = max([int(k) for k in play_urls if k.isdecimal() and requests.get(play_urls[str(k)]).ok])
    best_m3u8 = play_urls[str(best_res)]

    try:
        abr_m3u8 = play_urls['abr']
    except KeyError:
        abr_m3u8 = None

    return best_m3u8, abr_m3u8
