import sys
from DownloaderUtil import DownloaderUtil
from PdfDownloader import PdfDownloader


class DocumentsDownloader:
    def __init__(self):
        pass


def main():
    args = sys.argv[1:]
    if len(args) == 4 and args[0] == '-doctype' and args[2] == '-url':
        doctype = args[1]
        url = args[3]
        dlu = DownloaderUtil(url)
        dlu.check_validity()
        # url = "https://www.michigan.gov/sos/"
        # url = "https://www.michigan.gov/sos/0,4670,7-127-1631_50300_50310-30109--,00.html"
        pattern = url.split('/')[-1]
        if pattern == '':
            pattern = url.split('/')[-2]
        links = dlu.get_all_links('^/' + pattern + '/')
        for link in links:
            if doctype.lower() == 'pdf':
                PdfDownloader.download_pdfs(url+link)
    else:
        print("You enter incorrect input info. Please look at following example...\r\npython3 DocumentsDownloader.py -doctype pdf -url https://www.michigan.gov/sos/")


if __name__ == "__main__":
    main()