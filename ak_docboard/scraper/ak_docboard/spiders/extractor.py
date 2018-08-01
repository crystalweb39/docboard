from kyruus.scraper.cachespider import  DocBoardExtractor
from scrapy.selector import HtmlXPathSelector
from ak_docboard.items import AkDocboardItem

class Extractor(DocBoardExtractor):
    def check_cached_page(self, meta):
        return super(Extractor, self).check_cached_page(meta) and 'nhayer.exe' in meta['response_url']


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        item = AkDocboardItem()
        self.parse_meta(response, item)

        profile_table = hxs.select("//table")
        if not profile_table:
            return
        self.extract_doctor_profile(item, profile_table,
            {'address__street1': None, 'additional_information': ['Additional Information'],
             'license__first_state_licensure_date': None})

        item['cached_url'] = response.url
        address = hxs.select("//tr/td[contains(text(),'Address')]/following-sibling::td[1]/text()").extract()
        item['address'] = {'city_state_zip': address.pop(), 'other': address}

        yield item

