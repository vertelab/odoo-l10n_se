#!/usr/bin/python
# -*- coding: utf-8 -*-

from xlrd import open_workbook
from xlrd.book import Book
from xlrd.sheet import Sheet

import os

#wb = open_workbook(os.path.join(os.path.dirname(os.path.abspath(__file__)), u'Kontohändelser.xlsx'))
wb = open_workbook(os.path.join(os.path.dirname(os.path.abspath(__file__)), u'Kontohandelser.xlsx'))

ws = wb.sheet_by_name('Sheet1')
ws = wb.sheet_by_index(0)


#~ print ws.cell(0,0),ws.ncols,ws.nrows,ws.cell(3,10).value

#~ for r in range(ws.nrows):
    #~ if r > 3:
        #~ for c in ws.row(r):
            #~ print c.value



class Iterator(object):
    def __init__(self, data):
        self.row = 0
        self.data = data
        self.rows = data.nrows - 3
        self.header = [c.value.lower() for c in data.row(8)]
    
    def __iter__(self):
        return self

    def next(self):
        if self.row >= self.rows:
            raise StopIteration
        r = self.data.row(self.row + 3)
        self.row += 1
        return {self.header[n]: r[n].value for n in range(len(self.header))}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
