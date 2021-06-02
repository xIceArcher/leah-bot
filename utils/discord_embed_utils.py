from discord import Embed

def get_photo_embed(url: str, color: int = None):
    return Embed(color=color).set_image(url=url) if color else Embed().set_image(url=url)

def get_named_link(text: str, link: str):
    return f'[{text}]({link})'
