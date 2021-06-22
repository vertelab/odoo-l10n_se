#!/usr/bin/python
# -*- coding: utf-8 -*-

from xlrd import open_workbook
from xlrd.book import Book
from xlrd.sheet import Sheet

import os

wb = open_workbook(os.path.join(os.path.dirname(os.path.abspath(__file__)), u'unified_payments.csv'))

print
wb.nsheets

ws = wb.sheet_by_name('Sheet1')
ws = wb.sheet_by_index(0)


class Iterator(object):
    def __init__(self, data):
        self.row = 0
        self.data = data
        self.rows = data.nrows - 1
        self.header = [c.value.lower() for c in data.row(0)]

    def __iter__(self):
        return self

    def next(self):
        if self.row >= self.rows:
            raise StopIteration
        r = self.data.row(self.row + 1)
        self.row += 1
        return {self.header[n]: r[n].value for n in range(len(self.header))}


print
Iterator(ws).header

for r in Iterator(ws):
    print
    r

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
