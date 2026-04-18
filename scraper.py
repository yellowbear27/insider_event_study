
import requests
import time

from config import BASE_URL, HEADERS, REQUEST_DELAY_SECONDS

def fetch_page (url: str) -> str:
    response = requests.get(url, headers=HEADERS)
    time.sleep(REQUEST_DELAY_SECONDS)
    return response.text
