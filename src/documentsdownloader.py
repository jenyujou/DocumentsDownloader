##==============================================================#
## SECTION: Imports                                             #
##==============================================================#

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set
from urllib.parse import ParseResult, urljoin, urlparse, urlunsplit
import json
import logging
import posixpath
import os.path as op
import sys

from bs4 import BeautifulSoup
from pathvalidate import sanitize_filename
import click
import requests

##==============================================================#
## SECTION: Global Definitions                                  #
##==============================================================#

OPTIONS = {
    'log': [ # TODO: Handle logs better.
        click.option('--log-level', default='info', show_default=True, type=click.Choice(['info', 'debug', 'warning', 'error', 'none'], case_sensitive=True), help='Logging level.')
    ],
    'exts': [
        click.option('--doctype', default=['pdf'], show_default=True, multiple=True, help='Document types to locate/download.'),
        click.option('--ext', multiple=True, help='Extensions to locate/download.')
    ],
    'locate': [
        click.option('--locate-outfile', default='__output__/locations-{exts}-{target}.json', show_default=True, help='Save location info to given file path, overwrites existing. Use {exts} and {target} to autofill those values.'),
        click.argument('target')
    ],
    'download': [
        click.option('--download-outdir', default='__output__', show_default=True, help='Directory to download located files, overwrites existing files.')
    ]
}

DOCTYPE_MAP = {
    'doc': ['doc', 'docx'],
    'excel': ['csv', 'xls', 'xlsx', 'xlt', 'xla', 'xml'],
    'image': ['jpg', 'jpeg', 'png', 'gif', 'tiff'],
    'pdf': ['pdf']
}

##==============================================================#
## SECTION: Class Definitions                                   #
##==============================================================#

@dataclass
class Location:
    target: str
    source: str
    docurl: str
    docext: str
    extra: Dict[str, str] = field(default_factory = lambda: {})

    def outpath(self, basedir) -> Path:
        parsed = urlparse(self.docurl)
        pathsegs = parsed.path.strip('/').split('/')
        parts = [parsed.scheme + '___' + parsed.netloc] + pathsegs
        relpath = op.join(*[sanitize_filename(part) for part in parts])
        if not relpath.lower().endswith(self.docext):
            relpath += self.docext
        return Path(op.normpath(op.join(basedir, relpath)))

class BaseLocator(object):
    def __init__(self, target, exts):
        self.target = target
        self.exts = exts
        self.visited: Set[str] = set()
        self.locations: List[Location] = []

class JsonLocator(BaseLocator):
    def __init__(self, target, exts):
        super().__init__(target, exts)
        self.target = op.realpath(target)
        with open(self.target) as fi:
            for locdata in json.load(fi):
                location = Location(**locdata)
                if location.docext in exts:
                    self.locations.append(location)
        logging.info(f'Read {len(self.locations)} doc locations from file')

class TxtLocator(BaseLocator):
    def __init__(self, target, exts):
        super().__init__(target, exts)
        self.target = op.realpath(target)
        with open(self.target) as fi:
            for docurl in fi.read().splitlines():
                docext = op.splitext(docurl)[1]
                if docext in exts:
                    self.locations.append(Location(self.target, self.target, docurl, docext))
        logging.info(f'Read {len(self.locations)} doc locations from file')

class DocumentCenterLocator(BaseLocator):
    def __init__(self, target, exts):
        super().__init__(target, exts)
        self.base = urlparse(target)
        logging.info(f'Starting locator at {self.target}')
        logging.info(f'Locating file extensions: {self.exts}')
        soup = get_soup(self.target)
        if soup:
            tags = soup.select('div.t-mid')
            for tag in tags:
                path = tag.select('span.t-in')[0].text
                value = tag.select('input.t-input')[0].get('value')
                self.visit(path, value)
        logging.info(f'Completed locating, visited {len(self.visited)} pages, located {len(self.locations)} docs')

    def visit(self, path, value) -> None:
        url = to_absolute_url(self.base, urlparse('Home/Document_AjaxBinding'))
        self.visited.add(value)
        logging.info(f'Visiting {url} Value={value}')
        docs = DocumentCenterLocator.send_post(url, {'id': value})
        for doc in docs['data']:
            docext = '.' + doc['FileType']
            if docext in self.exts:
                docurl = to_absolute_url(self.base, urlparse(doc['URL']))
                extra = {'dir': path, 'name': doc['DisplayName']}
                self.locations.append(Location(self.target, url, docurl, docext, extra))
        logging.info(f'Current total found doc locations: {len(self.locations)}')
        self.crawl(path, value)

    def crawl(self, path, value) -> None:
        url = to_absolute_url(self.base, urlparse('Home/_AjaxLoading'))
        subdirs = DocumentCenterLocator.send_post(url, {'Value': value})
        for subdir in subdirs:
            subpath = op.join(path, subdir['Text'])
            subvalue = subdir['Value']
            is_unvisited = subvalue not in self.visited
            if is_unvisited:
                self.visit(subpath, subvalue)

    @staticmethod
    def send_post(url: str, body) -> Any:
        try:
            headers = {
              'X-Requested-With': 'XMLHttpRequest',
              'getDocuments': '1',
            }
            response = requests.post(url, headers=headers, data=body)
            return response.json()
        except Exception:
            logging.error(f'Could not retrieve content from URL: {url}')

class WebLocator(BaseLocator):
    VISITED_LIMIT = 250
    def __init__(self, target, exts):
        super().__init__(target, exts)
        self.base = get_baseurl(target)
        self.path = urlparse(target).path
        self.skipped_urls = set()
        self.visited_hashes = set()
        logging.info(f'Starting locator at {self.target}')
        logging.info(f'Locating file extensions: {self.exts}')
        self.visit(self.target)
        logging.info(f'Completed locating, visited {len(self.visited)} pages, located {len(self.locations)} docs')

    def is_visitable(self, url: str) -> bool:
        if len(self.visited) >= WebLocator.VISITED_LIMIT:
            return False
        if url in self.skipped_urls:
            return False
        if is_crawl_loop(url):
            return False
        ext = op.splitext(url)[1].lower()
        if ext:
            if ext in ['.com', '.net', '.org', '.gov', '.html', '.htm', '.php', '.asp', '.aspx']:
                return True
            if ext in ['.iso', '.exe', '.dmg'] + get_all_doctype_exts():
                return False
            try:
                response = requests.head(url, allow_redirects=True)
                return 'text/html' in response.headers['Content-Type']
            except Exception:
                logging.warning(f'Could not check content type of URL: {url}')
                return False
        return True

    def visit(self, url: str) -> None:
        if not self.is_visitable(url):
            self.skipped_urls.add(url)
            logging.debug(f'Skipping visit to {url}')
            return
        self.visited.add(url)
        logging.info(f'Visiting page {len(self.visited)} (limit={WebLocator.VISITED_LIMIT}) URL: {url}')
        try:
            soup = get_soup(url)
            souphash = hash(soup)
            if soup and souphash not in self.visited_hashes:
                self.visited_hashes.add(souphash)
                self.find_locations(url, soup)
                self.crawl(url, soup)
        except Exception:
            logging.error(f'Could not visit URL: {url}')

    def crawl(self, url: str, soup: BeautifulSoup) -> None:
        parsed_url = urlparse(url)
        for tag in soup.find_all('a', recursive=True):
            href = tag.get('href')
            if href:
                linkurl = to_absolute_url(parsed_url, urlparse(href))
                is_unvisited = linkurl not in self.visited
                if is_unvisited and WebLocator.is_subpage(self.target, linkurl):
                    self.visit(linkurl)

    @staticmethod
    def is_subpage(base_url: str, subpage_url: str) -> bool:
        return remove_scheme(subpage_url).startswith(remove_scheme(base_url))

    def find_locations(self, url: str, soup: BeautifulSoup) -> None:
        selector = ', '.join([f'a[href*="{ext}" i]' for ext in self.exts])
        for tag in set(soup.select(selector)):
            docurl = to_absolute_url(urlparse(url), urlparse(tag['href']))
            docext = op.splitext(urlparse(docurl).path)[1].lower()
            if docext in self.exts:
                self.locations.append(Location(self.target, url, docurl, docext))
        logging.info(f'Current total found doc locations: {len(self.locations)}')

##==============================================================#
## SECTION: Function Definitions                                #
##==============================================================#

def is_crawl_loop(url: str, repeat_limit: int=3) -> bool:
    parsed = urlparse(url)
    pathsegs = [seg for seg in parsed.path.split('/') if seg]
    repeats = 0
    prev = ''
    for seg in pathsegs:
        if seg == prev:
            repeats += 1
            if repeats >= (repeat_limit - 1):
                return True
        else:
            repeats = 0
        prev = seg
    return False

def find_all_exts(locate_outfile: str) -> List[str]:
    exts = set()
    with open(locate_outfile) as fi:
        for locdata in json.load(fi):
            exts.add(locdata['docext'])
    return sorted(exts)

def find_files(locate_outfile: str, download_outdir: str, exts: List[str]=[]) -> Dict[Path, List[Location]]:
    if not op.isfile(locate_outfile):
        logging.error(f'Could not find location file: {locate_outfile}')
        return {}
    if not op.isdir(download_outdir):
        logging.error(f'Could not find download output directory: {download_outdir}')
        return {}
    if not exts:
        exts = find_all_exts(locate_outfile)
    locator = JsonLocator(locate_outfile, exts)
    files = {}
    for location in locator.locations:
        outpath = location.outpath(download_outdir)
        if outpath.exists():
            files.setdefault(outpath, [])
            files[outpath].append(location)
    return files

def to_absolute_url(parsed_base: ParseResult, parsed_url: ParseResult) -> str:
    is_relative = not parsed_url.scheme and not parsed_url.netloc
    if is_relative:
        _format_url = lambda path: urlunsplit([parsed_base.scheme, parsed_base.netloc, path, '', '']).rstrip('/').strip()
        if not parsed_url.path:
            return parsed_base.geturl()
        is_path_from_root = parsed_url.path.startswith('/')
        if is_path_from_root:
            return _format_url(parsed_url.path)
        is_base_ext_page = bool(op.splitext(parsed_base.path)[1])
        if is_base_ext_page:
            return _format_url(urljoin(parsed_base.path, parsed_url.path))
        path = posixpath.normpath(f'{parsed_base.path}/{parsed_url.path}'.replace('//', '/'))
        if parsed_url.path.endswith('/') and not path.endswith('/'):
            path += '/'
        return _format_url(path)
    return parsed_url.geturl().strip()

def remove_scheme(url: str) -> str:
    parsed = urlparse(url)
    return urlunsplit(['', parsed.netloc, parsed.path, '', ''])

def get_soup(url: str, debug=False) -> BeautifulSoup:
    try:
        response = requests.get(url)
        if response.status_code == 404:
            logging.warning(f'Page not found: {url}')
            return
        if response.status_code >= 400:
            logging.warning(f'Bad response: {url}')
            return
        content = response.content
        if debug:
            Path('__debug__').mkdir(parents=True, exist_ok=True)
            dbgpath = f'__debug__/visited_content-{sanitize_filename(url)}.html'
            with open(dbgpath, 'w') as fo:
                fo.write(str(content))
        return BeautifulSoup(content, 'html.parser')
    except IOError:
        logging.error(f'Could not retrieve content from URL: {url}')

def get_locator(target, exts) -> BaseLocator:
    if op.isfile(target):
        target_ext = op.splitext(target)[1]
        if target_ext == '.json':
            return JsonLocator(target, exts)
        return TxtLocator(target, exts)
    path = urlparse(target).path
    if path.lower().strip('/') == 'documentcenter':
        return DocumentCenterLocator(target, exts)
    return WebLocator(target, exts)

def format_outfile_name(outfile, target, exts):
    if op.isfile(target):
        return outfile
    exts = '_'.join(exts).replace('.', '')
    return outfile.format(exts=exts, target=sanitize_filename(target, replacement_text='_'))

def locate(target, doctype, ext, locate_outfile, log_level) -> BaseLocator:
    exts = get_extensions(doctype, ext)
    locator = get_locator(target, exts)
    locate_outfile = format_outfile_name(locate_outfile, target, exts)
    is_target_file = op.isfile(target)
    is_outfile_dir = op.isdir(locate_outfile)
    if locate_outfile and not is_target_file and not is_outfile_dir:
        logging.info(f'Writing location info to {locate_outfile}')
        outdir = Path(op.dirname(op.realpath(locate_outfile)))
        outdir.mkdir(parents=True, exist_ok=True)
        outfile = Path(locate_outfile)
        locations = [asdict(location) for location in locator.locations]
        with outfile.open('w') as fo:
            json.dump(locations, fo, indent=4)
    return locator

def download(target, doctype, ext, locate_outfile, log_level, download_outdir) -> None:
    locator = locate(target, doctype, ext, locate_outfile, log_level)
    outdir = Path(op.realpath(download_outdir))
    outdir.mkdir(parents=True, exist_ok=True)
    locations = get_unique_locations(locator.locations)
    total_locations = len(locations)
    logging.info(f'Starting download of {total_locations} unique docs')
    for num, location in enumerate(locations, 1):
        try:
            outpath = location.outpath(download_outdir)
            outpath.parent.mkdir(parents=True, exist_ok=True)
            logging.info(f'Downloading doc {num} of {total_locations}: {outpath}')
            content = requests.get(location.docurl).content
            with outpath.open('wb') as fo:
                fo.write(content)
        except Exception:
            logging.error(f'Could not download/write {location.docurl}')

def get_unique_locations(locations: List[Location]) -> List[Location]:
    unique = []
    docurls = set()
    for location in locations:
        if location.docurl not in docurls:
            unique.append(location)
            docurls.add(location.docurl)
    return unique

def get_baseurl(url) -> ParseResult:
    parsed = urlparse(url)
    return urlparse(urlunsplit([parsed[0], parsed[1], '', '', '']))

def get_all_doctype_exts() -> List[str]:
    all_exts = []
    for exts in DOCTYPE_MAP.values():
        for ext in exts:
            all_exts.append('.' + ext)
    return sorted(set(all_exts))

def get_extensions(doctypes, extensions) -> List[str]:
    parsed_extensions = list(extensions)
    for dtype in doctypes:
        from_map = DOCTYPE_MAP.get(dtype, [])
        if not from_map:
            logging.warning(f'Could not find extensions for doctype: {dtype}')
        else:
            parsed_extensions += from_map
    return sorted(set(['.' + ext.lstrip('.').lower() for ext in parsed_extensions]))

def add_options(option_name) -> Any:
    def _add_options(func):
        for option in reversed(OPTIONS.get(option_name)):
            func = option(func)
        return func
    return _add_options

@click.group(help='Utility for locating and downloading documents of interest from websites.')
def cli_group(**kwargs) -> None:
    pass

@cli_group.command(name='locate', help='Locate documents from target.')
@add_options('exts')
@add_options('locate')
@add_options('log')
def cli_locate(target, doctype, ext, locate_outfile, log_level) -> None:
    try:
        locate(target, doctype, ext, locate_outfile, log_level)
    except KeyboardInterrupt:
        logging.error(f'Exiting due to user request.')
        sys.exit(1)

@cli_group.command(name='download', help='Locate and download documents from target.')
@add_options('exts')
@add_options('locate')
@add_options('download')
@add_options('log')
def cli_download(target, doctype, ext, locate_outfile, log_level, download_outdir) -> None:
    try:
        download(target, doctype, ext, locate_outfile, log_level, download_outdir)
    except KeyboardInterrupt:
        logging.error(f'Exiting due to user request.')
        sys.exit(1)

@cli_group.command(name='extensions', help='List extensions parsed from options.')
@add_options('exts')
def cli_extensions(doctype, ext) -> None:
    exts = get_extensions(doctype, ext)
    print(exts)

@cli_group.command(name='doctypes', help='List the available doctypes.')
def cli_doctypes() -> None:
    print(sorted(DOCTYPE_MAP.keys()))

##==============================================================#
## SECTION: Main Body                                           #
##==============================================================#

if __name__ == '__main__':
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
    cli_group()
