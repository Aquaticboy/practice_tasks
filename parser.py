import xml.etree.ElementTree as ET
import requests
import gzip
import shutil
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from urllib.parse import urlparse, parse_qs
import time
from selenium.common.exceptions import NoSuchElementException
import tempfile
import csv

PATH = r"C:\Program Files (x86)\chromedriver.exe"
service = Service(PATH)

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(service=service, options=options)

filename = "google_play_data.csv"

with open(filename, mode='w', newline='') as file:
    writer = csv.writer(file, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["Program ID", "Program Name", "Program Vendor"])


def process_url(url):
    driver.get(url)
    time.sleep(1)

    parsed_url = urlparse(url)
    parsed_qs = parse_qs(parsed_url.query)
    program_id = parsed_qs.get('id', [None])[0]

    try:
        program_name_element = driver.find_element(By.CSS_SELECTOR, '[itemprop="name"]')
        program_name = program_name_element.text.strip()

        program_vendor_elements = driver.find_elements(By.CSS_SELECTOR, '[class="zjgV1c"]')
        if len(program_vendor_elements) >= 2:
            program_vendor = program_vendor_elements[1].text.strip()
        else:
            program_vendor = None
    except NoSuchElementException:
        program_name = None
        program_vendor = None

    if program_id and program_name:
        print(f"Program ID: {program_id}")
        print(f"Program Name: {program_name}")
        print(f"Program Vendor: {program_vendor}")

        with open(filename, mode='a', newline='') as file:
            writer = csv.writer(file, delimiter=';', quoting=csv.QUOTE_MINIMAL)
            writer.writerow([program_id, program_name, program_vendor])
    else:
        print("Program ID or name is missing, skipping...")


sitemap_index_url = 'https://play.google.com/sitemaps/sitemaps-index-0.xml'
response = requests.get(sitemap_index_url)
response.raise_for_status()

root = ET.fromstring(response.content)
namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
count = 0

try:
    for loc_element in root.findall('ns:sitemap/ns:loc', namespace):
        gz_url = loc_element.text
        print(f"Processing .xml.gz URL: {gz_url}")

        gz_response = requests.get(gz_url)
        gz_response.raise_for_status()
        with gzip.open(BytesIO(gz_response.content), 'rb') as f_in:
            with tempfile.NamedTemporaryFile(delete=False) as temp_xml:
                shutil.copyfileobj(f_in, temp_xml)
                temp_xml_path = temp_xml.name

        extracted_tree = ET.parse(temp_xml_path)
        extracted_root = extracted_tree.getroot()

        for url_element in extracted_root.findall('ns:url/ns:loc', namespace):
            program_url = url_element.text
            print(f"------------------------------------")
            print(f"Processing Google Play's program/book/audiobook/film URL: {program_url}")
            process_url(program_url)

            count += 1
            if count >= 3:
                break
        if count >= 3:
            break
finally:
    driver.quit()
