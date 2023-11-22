from urllib.parse import urlparse

def get_base_url(url):
    parsed_url = urlparse(url)
    base_url = parsed_url.netloc
    return base_url
