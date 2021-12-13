import keyword
import re
import sys
import requests
from bs4 import BeautifulSoup


class DownloaderUtil:
    def __init__(self, url):
        self.url = url

    def check_validity(self):
        try:
            requests.get(self.url)
        except IOError:
            print("Invalid URL")
            sys.exit()

    def get_all_links(self, attr) :
        page = requests.get(self.url)
        soup = BeautifulSoup(page.content, "html.parser")
        links = []
        for link in soup.findAll('a', recursive=True, attrs={'href': re.compile(attr)}):
            links.append(link.get('href').split('/')[-1])
        return links


