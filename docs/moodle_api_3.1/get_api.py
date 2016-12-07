#!/usr/bin/env python3
import requests

from bs4 import BeautifulSoup as BS
from bs4 import SoupStrainer as SS

import code
import ast

url = 'https://demo.moodle.net'
ws_api = '/admin/webservice/documentation.php'
login = '/login/index.php'
logindata = {'username': 'admin', 'password': 'sandbox'}


def main():

    s = requests.Session()

    #get cookies
    r = s.post(url + login, data=logindata)
    r = s.get(url+ws_api)

    main_strain = SS(id='region-main')
    main_soup = BS(r.text, 'html.parser', parse_only=main_strain)

    parse_api(main_soup)
    return main_soup

def parse_api(soup):
    cmd_divs = soup.find_all(attrs={'class': 'collapsibleregion collapsed'})
    for cmd_div in cmd_divs:
        title_soup = cmd_div.div.find_all('div', class_='collapsibleregioncaption')
        func_name = title_soup[0].strong.contents[0]
        func_soup = cmd_div.div.find_all('div', class_='collapsibleregioninner')
        code.interact(local=locals())
        func_description = func_soup[0].div.contents[0]
        with open(func_name + '.html', 'w') as f:
            f.write(str(func_soup[0]))


if __name__ == '__main__':
    print(main())

