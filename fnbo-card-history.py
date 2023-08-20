#!/usr/bin/env python

import json
from dataclasses import dataclass
import sys

import click

@dataclass
class Transaction:
    description: str
    amount: float
    transaction_date: str

def get_json_url(account: str, data_count: int) -> str:
    return f'https://www.transaction.card.fnbo.com/v1/credit-card-accounts/{account}/posted-transactions?nextKey=0&pageSize={data_count}'


@click.command()
# If the URL of your FNBO card webpage looks like https://www.transaction.card.fnbo.com/accounts/summary/ABCD,
# ABCD is your account number
@click.option('--account', prompt='Account ID of your FNBO credit card.')
@click.option('--data-count', type=int, default=300, help='The number of data you want to get')
@click.option('--data-file', type=str, help='A path to file if you have already downloaded the data')
def main(account, data_count, data_file=None):
    if not data_file:
        url = get_json_url(account, data_count)
        print(f'Open {url} on your browser')
        json_file = input('Save the content to a json file and input the file name: ')
    else:
        json_file = data_file
    with open(json_file, 'r', encoding='utf-8') as f:
        transaction_data = json.load(f)
    transactions = transaction_data['creditCardTransactions']
    all_data = []
    for data in transactions:
        if data['description'] == 'ONLINE PAYMENT THANK YOU':
            # if the entry is about a payment you made, description should be 'ONLINE PAYMENT THANK YOU'
            continue
        d = Transaction(data['description'], -data['amount'], data['transactionDate'])
        all_data.append(d)
    sorted_all_data = sorted(all_data, key=lambda x: x.transaction_date)
    for item in reversed(sorted_all_data):
        print(f'{item.transaction_date},{item.amount},{item.description}')


if __name__ == '__main__':
    main()
