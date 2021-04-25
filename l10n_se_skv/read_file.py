#!/usr/bin/python
# -*- coding: utf-8 -*-

import csv

import os

csvfile = open('bokf_test.skv')

reader = csv.DictReader(csvfile)

#print reader
#print list(csv.reader(csvfile))

class Iterator(object):
    def __init__(self, data):
        self.row = 0
        self.data = list(csv.reader(data))
        self.ib = self.data[0][2]
        self.ub = sum([c[2] for c in self.data if c[1][:14] == u'Utgående saldo' ])
        for c in self.data:
            print('c%s' % c[3])
        print('ib %s' % self.ib)

    def __iter__(self):
        return self

    def next(self):
        if self.row >= self.rows:
            raise StopIteration
        r = self.data.row(self.row + 3)
        self.row += 1
        return {self.header[n]: r[n].value for n in range(len(self.header))}




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
