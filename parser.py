from bs4 import BeautifulSoup

def get_page_title(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.title

    if title_tag is None:
        return "No title found"

    return title_tag.text.strip()
