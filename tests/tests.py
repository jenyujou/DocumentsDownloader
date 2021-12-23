import os.path as op
import sys; sys.path.append(op.realpath(op.join(op.dirname(op.realpath(__file__)), '../src')))
import unittest

from documentsdownloader import DocumentCenterLocator, Location, WebLocator, is_crawl_loop

class TestIsCrawlLoop(unittest.TestCase):

    def test_can_detect_four_repeated_path_segs(self):
        self.assertTrue(is_crawl_loop('Visiting https://www.google.com/intl/en/ads/home/home/home/home/how-it-works', 4))

    def test_can_detect_four_repeated_path_segs_with_lower_limit(self):
        self.assertTrue(is_crawl_loop('Visiting https://www.google.com/intl/en/ads/home/home/home/home/how-it-works', 2))

    def test_can_ignore_four_repeated_path_segs_due_to_limit(self):
        self.assertFalse(is_crawl_loop('Visiting https://www.google.com/intl/en/ads/home/home/home/home/how-it-works', 5))

    def test_can_ignore_four_noncontiguous_repeated_path_segs(self):
        self.assertFalse(is_crawl_loop('Visiting https://www.google.com/intl/en/ads/home/home/other/home/home/how-it-works', 4))

class TestLocation(unittest.TestCase):

    def test_can_handle_upper_ext_in_docurl(self):
        common = "https://eforms.state.gov/"
        docurl = "https://eforms.state.gov/Forms/ds1664.PDF"
        location = Location(common, common, docurl, '.pdf')
        self.assertTrue(str(location.outpath('.')).endswith('ds1664.PDF'))

    def test_can_handle_missing_ext_in_docurl(self):
        common = "https://eforms.state.gov/"
        docurl = "https://eforms.state.gov/Forms/ds1664"
        location = Location(common, common, docurl, '.pdf')
        self.assertTrue(str(location.outpath('.')).endswith('ds1664.pdf'))

class TestDocumentCenterLocator(unittest.TestCase):

    def test_can_crawl(self):
        locator = DocumentCenterLocator('http://www.co.anson.nc.us/documentcenter', ['.pdf'])
        self.assertGreater(len(locator.locations), 100)
        self.assertGreater(len(locator.visited), 10)

class TestWebLocator(unittest.TestCase):

    def test_can_crawl(self):
        locator = WebLocator('https://pandoc.org/', ['.pdf'])
        self.assertGreater(len(locator.locations), 3)
        self.assertGreater(len(locator.visited), 3)

    def test_can_locate_pdfs(self):
        locator = WebLocator('https://www.ssa.gov/forms/ha-4632.html', ['.pdf'])
        self.assertEqual(1, len(locator.locations))
        self.assertEqual('https://www.ssa.gov/forms/ha-4632.pdf', locator.locations[0].docurl)
        self.assertEqual(1, len(locator.visited))

    def test_can_locate_pdfs_with_uppercase_ext(self):
        locator = WebLocator('https://eforms.state.gov/', ['.pdf'])
        self.assertGreater(len(locator.locations), 10)

    def test_should_not_locate_anything_due_to_extension(self):
        locator = WebLocator('https://www.ssa.gov/forms/ha-4632.html', ['.xls'])
        self.assertEqual(0, len(locator.locations))
        self.assertEqual(1, len(locator.visited))

    def test_can_locate_images(self):
        locator = WebLocator('http://graytalentgroup.com/wp-content/uploads/2021/12', ['.png'])
        self.assertGreater(len(locator.locations), 10)
        self.assertEqual(1, len(locator.visited))

    def test_can_locate_excels(self):
        locator = WebLocator('https://sample-videos.com/download-sample-csv.php/', ['.csv'])
        self.assertGreater(len(locator.locations), 5)
        self.assertGreater(len(locator.visited), 1)

    def test_can_locate_docs(self):
        locator = WebLocator('https://sample-videos.com/download-sample-doc-file.php/', ['.doc'])
        self.assertGreater(len(locator.locations), 5)
        self.assertGreater(len(locator.visited), 1)

    def test_can_check_is_visitable(self):
        self.assertTrue(WebLocator('test', []).is_visitable('https://semver.org/spec/v2.0.0-rc.1.html'))
        self.assertTrue(WebLocator('test', []).is_visitable('https://docs.getpelican.com/en/4.6.0'))
        self.assertTrue(WebLocator('test', []).is_visitable('https://docs.getpelican.com/en/4.6.0/'))
        self.assertTrue(WebLocator('test', []).is_visitable('https://docs.python.org/3/library/urllib.parse.html'))

    def test_can_check_is_not_visitable(self):
        self.assertFalse(WebLocator('test', []).is_visitable('https://www.arlis.org/docs/sysadm/SW_DVD5_Office_Professional_Plus_2016_W32_English_MLF_X20-41353.ISO'))
        self.assertFalse(WebLocator('test', []).is_visitable('https://www.arlis.org/docs/sysadm/SW_DVD5_Office_Professional_Plus_2016_W32_English_MLF_X20-41353.ISO'))

if __name__ == '__main__':
    unittest.main()
