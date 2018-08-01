import random
import sys
import time
import itertools

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.conf import settings
from scrapy.selector import HtmlXPathSelector
from scrapy.http import FormRequest
from scrapy.exceptions import CloseSpider

from kyruus.data.scraper import generate_name
from kyruus.scraper.utils import ParseUtils


def urljoin(response, ref):
    '''Converts relative URLs to absolute while preserving
    absolute URLs'''
    from scrapy.utils.url import urljoin_rfc
    from scrapy.utils.response import get_base_url

    return urljoin_rfc(get_base_url(response), ref)


class KyruusSpider(BaseSpider):
    total = 0
    current = 0

    def log_next_page(self, freq=1):
        ''' Set total to number of pages, when possible, and call this function for every page out of total. '''

        if self.total == 0:
            if self.current == 0:
                self.log("self.total not set", log.ERROR)
            return

        self.current += 1

        if self.current % freq == 0 or self.current == self.total:
            self.log("Page: %i of %i" % (self.current, self.total), log.INFO)

            if settings['RUN_ID']:
                from kyruus.recrawler.state import RecrawlDatabase

                progress = round(float(self.current) / self.total, 3) if self.total else None
                try:
                    RecrawlDatabase().heartbeat(settings['RUN_ID'], progress)
                except Exception as e:
                    self.log("Heartbeat error: %r" % e, log.WARNING)

    def xpath_extract(self, item, key, hxs, path,
                      empty_ok=False,
                      trans=lambda x: x.strip()):
        '''Populates an item with a single value from an
        HTMLXPathSelector with an optional transformation.

        An optional translation can be supplied.  By default this
        strips whitespace from the ends of extracted strings.'''
        result = hxs.select(path).extract()
        if len(result) > 1:
            self.log('%s: extra results for path: %s' %
                     (sys._getframe().f_code.co_name, path),
                     log.WARNING)
        if len(result):
            result = trans(result[0])
            if result:
                item[key] = result
        else:
            if not empty_ok:
                self.log('%s: empty result for selector: %s' %
                         (sys._getframe().f_code.co_name, path),
                         log.WARNING)

        return result

    def xpath_list(self, hxs, path, trans=lambda x: x.strip(),
                   skip_empty=True):
        '''Collects a list of XPath entries using extract.

        An optional translation can be supplied.  By default this
        strips whitespace from the ends of extracted strings.

        By default any empty strings are skipped.  The skip_empty
        parameter can be set to false to change this.
        '''
        result = []
        for thing in hxs.select(path):
            value = trans(thing.extract())
            if value or not skip_empty:
                result.append(value)
        return result


class KyruusCrawlSpider(KyruusSpider):
    name = generate_name() + '_crawler'

    def letters(self, shuffle=True):
        ''' Return a list of letters from "a" to "z", shuffled randomly. '''

        a = range(0, 26)
        if shuffle:
            random.shuffle(a)
        return [chr(ord('a') + n) for n in a]

    def create_person_names(self, length=1, suffix=None):
        '''
        Creates a list of combinations of letters a-z of the specified length.
        If required length > 1 than adds names like O'
        '''

        names = ["".join(n) for n in itertools.product(self.letters(False), repeat=length)]

        # names like O'Brien
        if length > 1:
            names.extend([n + "'" for n in self.letters(False)])

        if suffix:
            names = [n + suffix for n in names]

        return names

    def delete_cached_request(self, request):
        ''' Delete a cached request from FilesystemCacheStorage. Returns True if successful. '''

        import os.path
        from shutil import rmtree
        from scrapy.utils.request import request_fingerprint

        if not settings['HTTPCACHE_ENABLED'] and not 'httpcache.FilesystemCacheStorage' in settings['HTTPCACHE_STORAGE']:
            self.log('HTTPCACHE is disabled or HTTPCACHE_STORAGE is not FilesystemCacheStorage.', log.ERROR)
            return False

        if not request and not isinstance(request, 'scrapy.http.request.Request'):
            raise TypeError('Invalid argument "request"')
        req_fp = request_fingerprint(request)
        req_dir = os.path.join('.scrapy', settings['HTTPCACHE_DIR'], self.name, req_fp[:2], req_fp)
        if not os.path.exists(req_dir):
            self.log('Path does not exist or permission denied %s' % req_dir, log.ERROR)
            return False

        try:
            rmtree(req_dir)
            self.log('Deleted cached request %s, url %s' % (req_dir, request.url), log.DEBUG)
            return True
        except Exception:
            self.log('Error deleting %s' % req_dir, log.ERROR)
            return False


class DocBoardSpider(KyruusCrawlSpider):
    """ Parent spider for all datasources under KYRUUS-6667 """
    __search_response = None
    docboard_state = None
    http_user = 'kyruus'
    http_pass = '968ky22'
    profile_count = 0
    total = 1
    keywords = []
    search_exceeded_message = 'search exceeded'
    site_is_down_message = "database server is being updated"
    profile_not_found_message = 'not found'
    profile_not_found_message_xpath = '//b[contains(text(), "not found")]'
    resume_counter = 0
    resume_limit = 6
    sleep_duration = 1800

    ### Dictionary for Extra parameters for Search request, where ever applicable
    search_formdata = None
    ### Flag to overide default form data. Default bahavior is to update default formdata dictionary
    override_search_formdata = False
    ### Dictionary for Extra parameters for profile request, where ever applicable
    profile_formdata = None
    ### XPath to make sure we are on right page before submitting search
    search_btn_xpath = None
    ### Xpath pointing to Doctor's name on profile page. Used in logging
    doc_name_xpath = "//table//tr[./td[contains(text(),'Licensee Name')]]/td[2]"

    def __init__(self):

        for a in self.letters(shuffle=False):
            for b in self.letters(shuffle=False):
                self.keywords.append(a + b)
        super(DocBoardSpider, self).__init__()

    def parse(self, response):
        self.delete_cached_request(response.request)
        self.log_next_page()
        self.__search_response = response
        hxs = HtmlXPathSelector(self.__search_response)
        if not hxs.select(self.search_btn_xpath):
            self.log("Not a search page", log.CRITICAL)
            return
        for search_request in self.generate_search_requests():
            yield search_request

    def generate_search_requests(self):
        for keyword in self.keywords:
            self.total += 1
            yield self.get_search_request(keyword)

    def search_result(self, response):
        self.log_next_page()
        if self.site_is_down_message in response.body:
            yield self.sleep_resume(response)
            return
        self.resume_counter = 0

        hxs = HtmlXPathSelector(response)
        if hxs.select("//*[contains(text(), 'not found')]"):
            self.log("No match for state %s, Keyword: %s" % (self.docboard_state, response.meta['keyword']))
            return

        if self.search_exceeded_message in response.body:
            ''' Handling record capping: Add more search request in case of capping on a search keyword '''
            self.log("Records are being capped for %s, adding detailed search requests" % response.meta['keyword'])
            for letter in self.letters(shuffle=False):
                self.total += 1
                yield self.get_search_request(response.meta['keyword'] + letter)
            return

        ids = hxs.select("//select[@name='mednumb']/option/@value").extract()
        id_count = len(ids)
        self.profile_count += id_count
        self.log("Search Results(%s) found: %s" % (response.meta['keyword'], id_count))
        self.log("TOTAL PROFILES FOUND: %s" % self.profile_count)

        self.total += id_count
        for id in ids:
            profiledata = {'form_id': 'medname',
                           'state': self.docboard_state,
                           'mednumb': id,
                           'lictype': 'ALL',
                           'medlname': response.meta['keyword'],
                           'medfname': '', }
            if self.profile_formdata:
                profiledata.update(self.profile_formdata)
            yield FormRequest.from_response(response,
                                            formdata=profiledata,
                                            meta={'keyword': response.meta['keyword']},
                                            callback=self.profile,
                                            errback=self.profile_errback
            )


    def search_result_errback(self, failure):
        self.log("Search Result failed: %s" % failure.getErrorMessage(), log.ERROR)

    def profile(self, response):
        self.log_next_page()
        if self.site_is_down_message in response.body:
            yield self.sleep_resume(response)
            return
        self.resume_counter = 0
        hxs = HtmlXPathSelector(response)
        if self.profile_not_found_message in response.body:
            not_found_message = ParseUtils.get_line_from_node(hxs.select(self.profile_not_found_message_xpath))
            self.log("Invalid Profile: %s" % not_found_message, log.INFO)
            return
        self.log("# Search: '%s', DOC: '%s'" % (response.meta['keyword'],
                                                ParseUtils.get_line_from_node(hxs.select(self.doc_name_xpath))))

    def profile_errback(self, failure):
        self.log("Profile Result failed: %s" % failure.getErrorMessage(), log.ERROR)

    def get_search_request(self, keyword):
        _formdata = {'LICTYPE': 'ALL',
                     'form_id': 'medname',
                     'state': self.docboard_state,
                     'medfname': '',
                     'medlicno': '', }

        if self.search_formdata and self.override_search_formdata:
            _formdata = self.search_formdata
        elif self.search_formdata:
            _formdata.update(self.search_formdata)

        _formdata['medlname'] = keyword
        return FormRequest.from_response(self.__search_response,
                                         formdata=_formdata,
                                         meta={'keyword': keyword},
                                         callback=self.search_result,
                                         errback=self.search_result_errback)

    def sleep_resume(self, response):
        self.delete_cached_request(response.request)
        if self.resume_counter == self.resume_limit:
            down_time = self.sleep_duration * self.resume_limit / self.resume_counter
            raise CloseSpider("Server has been down for %s mins" % down_time)

        self.resume_counter += 1
        self.log("[Resume Count %s] Server is down for maintenance. Request deleted from cache. Sleeping for %s min" %
                 (self.resume_counter, str(self.sleep_duration / 60)), log.WARNING)
        time.sleep(self.sleep_duration)
        self.total += 1
        return response.request