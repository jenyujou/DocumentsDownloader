import re
import sys
import requests
from bs4 import BeautifulSoup
from docDownloader import docdownloader as ddl
from excelDownloader import exceldownloader as ex
from imageDownloader import imagedownloader as im
from pdfDownloader import pdfdownloader as pf


class DocumentsDownloader:
    def __init__(self, url):
        self.url = url

    def check_validity(self):
        try:
            requests.get(self.url)
        except IOError:
            print("Invalid URL")
            sys.exit()

    def get_all_links(self, attr):
        page = requests.get(self.url)
        soup = BeautifulSoup(page.content, "html.parser")
        links = []
        for link in soup.findAll('a', recursive=True, attrs={'href': re.compile(attr)}):
            links.append(link.get('href').split('/')[-1])
        return links


def main():
    args = sys.argv[1:]
    if len(args) == 4 and args[0] == '--doctype' and args[2] == '--url':
        doctype = args[1]
        url = args[3]
        dd = DocumentsDownloader(url)
        dd.check_validity()
        pattern = url.split('/')[-1]
        if pattern == '':
            pattern = url.split('/')[-2]
        links = dd.get_all_links('^/' + pattern + '/')
        for link in links:
            if 'pdf' in doctype.lower():
                pf.PdfDownloader.download_pdfs(url + link)
            elif 'doc' in doctype.lower():
                ddl.DocDownloader.download_docs(url + link)
            elif 'excel' in doctype.lower():
                ex.ExcelDownloader.download_excels(url + link)
            elif 'image' in doctype.lower():
                im.ImageDownloader.download_images(url + link)
    else:
        print(
            "You enter incorrect input info. Please look at following example...\r\npython3 documentsdownloader.py --doctype pdf --url https://www.michigan.gov/sos/")


if __name__ == "__main__":
    main()
