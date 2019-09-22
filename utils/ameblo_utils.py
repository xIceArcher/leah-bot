import bs4
import requests


def get_ameblo_photo_urls(url: str):
    soup = bs4.BeautifulSoup(requests.get(url).content, 'html.parser')
    return [image['src'] for image in soup.find_all(class_='PhotoSwipeImage')]
