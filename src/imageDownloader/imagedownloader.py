import os
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup


class ImageDownloader:
    def __init__(self, url):
        self.url = url

    def download_images(self):
        # If there is no such folder, the script will create one automatically
        folder_location = os.getcwd() + r'webscraping'
        if not os.path.exists(folder_location):
            os.mkdir(folder_location)

        response = requests.get(self.url)
        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.select(
                "a[href*='.jpg'], a[href*='.jpeg'], a[href*='.png'], a[href*='.gif'], a[href*='.tiff']"):
            # Name the image files using the last portion of each link which are unique in this case
            filename = os.path.join(folder_location, link['href'].split('/')[-1])
            with open(filename, 'wb') as f:
                f.write(requests.get(urljoin(self.url, link['href'])).content)
