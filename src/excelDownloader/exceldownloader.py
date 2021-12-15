import os
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup


class ExcelDownloader:
    def __init__(self, url):
        self.url = url

    def download_excels(self):
        # If there is no such folder, the script will create one automatically
        folder_location = os.getcwd()+r'webscraping'
        if not os.path.exists(folder_location):
            os.mkdir(folder_location)

        response = requests.get(self.url)
        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.select("a[href*='.csv'], a[href*='.xls'], a[href*='.xlt'], a[href*='.xla'], a[href*='.xml']"):
            # Name the excel files using the last portion of each link which are unique in this case
            filename = os.path.join(folder_location, link['href'].split('/')[-1])
            with open(filename, 'wb') as f:
                f.write(requests.get(urljoin(self.url, link['href'])).content)