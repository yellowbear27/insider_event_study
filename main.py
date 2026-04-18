from scraper import fetch_page
from config import BASE_URL


def main():
    html = fetch_page(BASE_URL)
    print (html[:500])


if __name__ == "__main__":
  main()
