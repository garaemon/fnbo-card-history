#!/usr/bin/env python

import csv
import json
from dataclasses import dataclass
import pprint
import shutil
import sys
import time
from typing import Dict
from urllib.parse import urlparse, parse_qs, urlencode

import click
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService


@dataclass
class Transaction:
    description: str
    amount: float
    transaction_date: str


def get_json_url(account: str, data_count: int) -> str:
    return f'https://www.transaction.card.fnbo.com/v1/credit-card-accounts/{account}/posted-transactions?nextKey=0&pageSize={data_count}'


def get_post_transaction_request(driver: webdriver) -> Dict:
    # TODO: add timeout
    while True:
        browser_log = driver.get_log('performance')
        logs = [json.loads(lr["message"])["message"] for lr in browser_log]
        for log in logs:
            # https://chromedevtools.github.io/devtools-protocol/tot/Network/#event-requestWillBeSent
            if log['method'] == 'Network.requestWillBeSent':
                url = log['params']['request']['url']
                parsed_url = urlparse(url)
                if parsed_url.path.endswith('/posted-transactions'):
                    # pprint.pprint(log)
                    return log['params']['request']
        time.sleep(10)


@click.command()
@click.option('--username')
@click.option('--password')
@click.option('--output-file', default='output.csv')
def main(username, password, output_file):
    # Run browsermob-proxy to capture network access
    print('Opening the FNBO website and proceed with the sign-in process.')
    caps = DesiredCapabilities.CHROME
    chrome_options = ChromeOptions()
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    driver = webdriver.Chrome(options=chrome_options)

    driver.get('https://www.transaction.card.fnbo.com/')
    WebDriverWait(
        driver,
        20).until(lambda x: x.find_element(By.ID, "okta-signin-username"))

    username_element = driver.find_element(By.ID, 'okta-signin-username')
    username_element.clear()
    username_element.send_keys(username)
    password_element = driver.find_element(By.ID, 'okta-signin-password')
    password_element.clear()
    password_element.send_keys(password)

    form = driver.find_element(By.ID, 'form32')
    form.submit()
    WebDriverWait(driver, 120).until(
        EC.url_matches("https://www.transaction.card.fnbo.com/accounts/.*"))

    print(
        "We have arrived at the target URL. Proceed with the post process...")
    try:
        post_transaction_request = get_post_transaction_request(driver)
        parsed_url = urlparse(post_transaction_request['url'])
        query_params = parse_qs(parsed_url.query)
        query_params['pageSize'] = 300
        query_params['nextKey'] = 0
        url = f'{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{urlencode(query_params)}'
        result = requests.get(url, headers=post_transaction_request['headers'])
        json = result.json()
        write_result(json, output_file)
    finally:
        driver.quit()


def write_result(transaction_data: Dict, output_file: str) -> None:
    transactions = transaction_data['creditCardTransactions']
    all_data = []
    for data in transactions:
        if data['description'].strip() == 'ONLINE PAYMENT THANK YOU':
            # if the entry is about a payment you made, description should be 'ONLINE PAYMENT THANK YOU'
            pass
        else:
            print(data)
            d = Transaction(data['description'], data['amount'],
                            data['transactionDate'])
            all_data.append(d)
    sorted_all_data = sorted(all_data, key=lambda x: x.transaction_date)
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['date', 'payment', 'cost', 'category', 'payee'])
        for item in reversed(sorted_all_data):
            csv_writer.writerow([
                item.transaction_date, 'FNBO Card', item.amount, '',
                item.description
            ])


if __name__ == '__main__':
    main()
