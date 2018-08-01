from kyruus.scraper.kyruusspider import DocBoardSpider


class Crawler(DocBoardSpider):
    docboard_state = 'ak'
    start_urls = ['http://docboard.madriveraccess.com/%s/' % docboard_state]
    search_btn_xpath = "//input[@value='Name Search']"

    def generate_search_requests(self):
        for keyword in self.keywords:
            self.search_formdata = {'LICTYPE': 'MEDS'}
            self.total += 1
            yield self.get_search_request(keyword)
        for keyword in self.keywords:
            self.search_formdata = {'LICTYPE': 'MEDO'}
            self.total += 1
            yield self.get_search_request(keyword)
