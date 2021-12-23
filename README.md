# Documents Downloader

## Setup
  1. Install Python 3.7+, `python3` (or just `python`) as well as `pip` should be availabe shell commands afterwards.
  2. Install third-party packages by opening a shell to this directory and running: `pip install -r requirements.txt`

## Design
The `documentsdownloader.py` provides a CLI utility for locating and downloading documents of interest from websites. This functionality works as follows:

  1. The user provides doctypes and extensions of interest as well as a target (e.g. a URL like https://www.michigan.gov/sos/).
  2. The utility parses the provided doctypes and extensions into a final list of document extensions to locate.
  3. A Locator is picked based on the provided target.
  4. The Locator searches the target and compiles a list of Location info for each found document that matches a provided extension.
  5. The utility downloads the documents using the Location info.

The following Locators are provided:

  - `TxtLocator` - Reads document URLs from lines in a text file.
  - `JsonLocator` - Reads serialized Location info from a JSON file.
  - `WebLocator` - Crawls a website starting at the target URL. During a crawl, visited pages will be limited to the target path, e.g. a target of http://www.example.com/abc will only crawl pages under the `/abc` path, a page like http://www.example.com/def will be skipped. Document URLs found on crawled pages have no limitations, e.g. a document URL of http://www.another.com/doc.pdf can be located from http://www.example.com/abc.
  - `DocumentCenterLocator` - Crawls websites like https://www.annapolis.gov/DocumentCenter which use [CivicEngage DocumentCenter](https://www.civicengagecentral.civicplus.help/hc/en-us/articles/115004761614--Document-Center-Overview).

The Location info provides:

  - `target` - The target provided to the utility.
  - `source` - The source where the document was located, e.g. the crawled webpage URL if using `WebLocator`.
  - `docurl` - The URL to download the document.
  - `docext` - The extension of the document.
  - `extra` - A dictionary of extra info about the document.

By default, the Location info will be written to a JSON file. The provided extensions and target are autofilled in the output filename using the format `locations-{exts}-{target}.json`, e.g.:

    locations-docx_pdf-https___www.michigan.gov_sos_.json

## Usage
Open a shell at the `src/` folder and view the utility help info:

    python3 documentsdownloader.py --help

Each command also has help info:

    python3 documentsdownloader.py doctypes --help
    python3 documentsdownloader.py extensions --help
    python3 documentsdownloader.py locate --help
    python3 documentsdownloader.py download --help

To see available doctypes:

    python3 documentsdownloader.py doctypes

To see list of extensions for a given doctype:

    python3 documentsdownloader.py extensions --doctype image

To see resulting list of extensions when mixing doctypes and explicit extensions:

    python3 documentsdownloader.py extensions --doctype image --ext txt --ext csv

To crawl a website and save Location info:

    python3 documentsdownloader.py locate https://www.michigan.gov/sos/

To locate and download files:

    python3 documentsdownloader.py download https://www.michigan.gov/sos/

A Location json/txt file can be provided as a target to skip the locate step:

    python3 documentsdownloader.py download __output__/locations-docx_pdf-https___www.michigan.gov_sos_.json

## Limitations
Some known limitations:

  - Certain dynamic websites will return no Location info.
  - Cancelling the utility during the locate step (e.g. via CTRL+C) will result in lose of any current Location info, i.e. Location info is only written to the output file after the step has completed.
