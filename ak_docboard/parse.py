#!/usr/bin/env python

from kyruus.parser.parser import StateboardParser
from kyruus import person
import re

class Parser(StateboardParser):

    def preprocess_row(self, row):

        row['full_name']=" ".join(row['full_name'].split())
        row['license']['type']=" ".join(row['license']['type'].split())
        row['source_url']="http://docboard.madriveraccess.com/ak/"

        self.parse_first_middle_last_suffix(row['full_name'],row)

        if row.get('address'):
            if row['address'].get('other'):
                i=1
                for street in row['address']['other']:
                    street=" ".join(street.split())
                    cty_st_zp=re.findall(r'[A-Z]{4} [A-Z]{2} [0-9]{4}',street)
                    if cty_st_zp:
                       self.parse_city_state_zip(street,row['address'])
                    else:
                        num='street'+str(i)
                        row['address'][num]=street
                        i+=1

        if row.get(person.DISCIPLINARY_ACTION):
            if row[person.DISCIPLINARY_ACTION].get('name'):
                if (not "None" in row[person.DISCIPLINARY_ACTION].get('name') or not "None" in row[person.DISCIPLINARY_ACTION].get('description')) and row.get('additional_information'):
                    row[person.DISCIPLINARY_ACTION]['name']=row.get('additional_information')
                    del row[person.DISCIPLINARY_ACTION]['description']
                    date=re.findall(r'\d+/\d+/\d+',row.get('additional_information'))
                    if not date:
                        date=re.findall(r'\d+-\d+-\d+',row.get('additional_information'))
                    if date:
                        row[person.DISCIPLINARY_ACTION]['start_date']=date[0]
                else:
                    del row[person.DISCIPLINARY_ACTION]

        super(Parser, self).preprocess_row(row)


if __name__ == "__main__":
    Parser().parse()
