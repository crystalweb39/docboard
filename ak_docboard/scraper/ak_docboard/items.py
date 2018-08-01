# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/topics/items.html

from scrapy.item import Item, Field

class AkDocboardItem(Item):
    full_name = Field()
    gender = Field()
    source_url = Field()
    crawled_date = Field()
    cached_url = Field()

    address = Field()
    medical_school = Field()
    disciplinary_action = Field()
    license = Field()
    additional_information = Field()

