#!/usr/bin/python
# -*- coding: utf-8 -*-

import csv

with open(u'Download.CSV', 'rb') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        print(row['Name'], row['Fee'])


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
