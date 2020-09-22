#!/usr/bin/python
# -*- coding: utf-8 -*-

import re

CURRENCIES = {
    '208': u'Danska Kronor (DKK)',
    '978': u'Euro (EUR)',
    '840': u'US Dollar $ (USD)',
    '826': u'Engelska Pund £ (GBP)',
    '752': u'Svenska Kronor (SEK)',
    '036': u'Australiensiska Dollar (AUD)',
    '124': u'Kanadensiska Dollar (CAD)',
    '352': u'Isländska Kronor (ISK)',
    '392': u'Japanska Yen (JPY)',
    '554': u'New Zealändska Dollar (NZD)',
    '578': u'Norska Kronor (NOK)',
    '756': u'Schweiziska Franc (CHF)',
    '949': u'Turkiska Lire (TRY)',
}

def date_format(date):
    d = date.replace(' \n', '')
    return '%s-%s-%s %s' %(d[6:10], d[3:5], d[:2], d[-8:])

file = open(u'5146111__cleared__24_10_2018_14_50_01.txt', 'r')
lines = file.readlines()
title = lines[0]
identity = title[title.find('(')+1:title.find(')')].split(' ')[0]
period = '%s %s - %s %s' %(lines[5].split('kl.')[0].split(':')[1].strip(), lines[5].split('kl.')[1].strip(), lines[6].split('kl.')[0].split(':')[1].strip(), lines[6].split('kl.')[1].strip())
transactions = []
for l in lines[9:]:
    values = l.split(',')
    currency = CURRENCIES.get(values[3], '')
    transactions.append({
        'ordernr': values[0],
        'transaktionsnr': values[1],
        'amount': float(values[2]),
        'currency': currency[currency.find('(')+1:currency.find(')')].split(' ')[0] if currency != '' else '',
        'fee': float(values[4].replace('??', '0.00')),
        'type': values[5],
        'debpoint': date_format(values[6]),
    })

print transactions

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
