import os
import aiohttp
import asyncio

from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from . import constants as const
from .utils import get_pdf_count

class Colin_scraper(webdriver.Chrome):
    def __init__(self, driver_path=const.DRIVER_PATH):
        self.driver_path = driver_path
        os.environ['PATH'] += self.driver_path
        super(Colin_scraper, self).__init__()
        self.implicitly_wait(1)
        self.maximize_window()

    def open_reg_search_from_log_in(self):
        registry_search = self.find_element(By.XPATH, '//*[@id="servicesLeft"]/div/p[1]/a')
        registry_search.click()

    def open_log_in(self):
        self.get(const.LOG_IN_URL)

    def log_in(self):
        # find all log in elements 
        username = self.find_element(By.NAME, 'user')
        password = self.find_element(By.NAME, 'password')
        submit = self.find_element(By.NAME, 'nextButton')
        type_dropdown = Select(self.find_element(By.NAME, 'realmId'))

        # log in
        username.send_keys('mcai')
        password.send_keys('N0>{m8=6|2@o*2')
        type_dropdown.select_by_value('staff')
        submit.click()

    def search_org(self, org_num):
        # input corpNum
        corp_num = self.find_element(By.NAME, 'corpNum')
        corp_num.send_keys(org_num)
        submit = self.find_element(By.NAME, 'nextButton')
        submit.click()

    async def download_pdfs(self, cookies):
        # setup cookies
        cookies = {}
        for cookie in cookies:
                name = cookie['name']
                value = cookie['value']
                cookies[name] = value

        soup = self._setup_bs()

        # get all a_tags for pdfs
        all_pdf_a_tags = (soup.find_all('a', {"target": "View_Report"}, href=True))

        # download all PDFs
        pdf_dict = {}
        connector = aiohttp.TCPConnector(force_close=True)
        async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
            tasks = []
            # for each href setup callback to grab pdf data 
            for a_tag in all_pdf_a_tags:
                text = a_tag.text
                if text not in const.UNWANTED_TAGS:
                        count = get_pdf_count(pdf_dict, text)
                        href = a_tag.get('href')
                        href = 'https://www.corporateonline.gov.bc.ca' + href
                        tasks.append(asyncio.ensure_future(self._get_pdf(session, href, text, count)))

            # send requests to get all pdfs in parallel
            pdfs = await asyncio.gather(*tasks)
            # for now write all pdf data from mem into pdf files on disk
            for temp_pdf in pdfs:
                with open(f'{const.BASE_PATH}/' + temp_pdf['text'] + f'_{temp_pdf["count"]}' '.pdf', 'wb') as pdf:
                    pdf.write(temp_pdf['response'])

    # def _setup_session(self, cookies):
    #     # setup request session with log in cookies
    #     session = requests.Session()
    #     for cookie in cookies:
    #         session.cookies.set(cookie['name'], cookie['value'])
    #     return session

    def _setup_bs(self):
        # setup bs
        page_source = self.page_source
        soup = bs(page_source, 'lxml')
        return soup

    async def _get_pdf(session, href, text, count):
        async with session.get(href) as response:
            return {"response": await response.read(), "text": text, "count": count}
