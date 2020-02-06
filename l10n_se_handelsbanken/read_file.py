#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015-2016 Vertel AB <http://vertel.se>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from xlrd import open_workbook
from xlrd.book import Book
from xlrd.sheet import Sheet

import os

wb = open_workbook(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Transaktionsrapport.xls'))

print wb.nsheets

ws = wb.sheet_by_name('Transaktionsrapport')
#ws = wb.sheet(1)


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
        self.header = [c.value.lower() for c in data.row(1)]
    
    def __iter__(self):
        return self

    def next(self):
        if self.row >= self.rows:
            raise StopIteration
        r = self.data.row(self.row + 3)
        self.row += 1
        return {self.header[n]: r[n].value for n in range(len(self.header))}



for r in Iterator(ws):
    print r

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
