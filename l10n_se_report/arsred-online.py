# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2017 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

from lxml import html
import requests

import re

#~ import logging
#~ _logger = logging.getLogger(__name__)

def domain(konto):
    k = re.compile('(\d{4})')
    k_eller = re.compile('Konto (\d{4}-\d{4}) eller (\d{4}-\d{4})')
    k_eller2 = re.compile('Konto (\d{4}-\d{4}), (\d{4}-\d{4}) eller (\d{4}-\d{4})')
    s_eller = re.compile('Konto (\d{4}) eller (\d{4})')
    kl = re.compile('(\d{4})-(\d{4})')

    dom = []
    sign = ['>=','<=']
    andor = ['&','|','&']
    
    
    if u'förutom' in konto:
        if len(kl.findall(konto)) == 4 and len(k.findall(konto)) == 9:
            ke = kl.findall(konto)
            r0 = range(int(ke[0][0]),int(ke[0][1])+1)
            r1 = range(int(ke[1][0]),int(ke[1][1])+1)
            r2 = range(int(ke[2][0]),int(ke[2][1])+1)
            r3 = range(int(ke[3][0]),int(ke[3][1])+1)
            dom = r0 + r1 + r2 + r3
            dom.remove(int(k.findall(konto)[2]))
            return [('code','in', '[%s]' % ','.join([str(i) for i in dom]))]
            
        if len(kl.findall(konto)) == 4:
            ke = kl.findall(konto)
            r1 = range(int(ke[1][0]),int(ke[1][1])+1)
            r2 = range(int(ke[2][0]),int(ke[2][1])+1)
            r3 = range(int(ke[3][0]),int(ke[3][1])+1)
            return [('code','>=',ke[0][0]),('code','<=',ke[0][1]),('code','not in',' [%s]' % ','.join([str(i) for i in r1 + r2 + r3]))]
        if len(kl.findall(konto)) == 3:
            ke = kl.findall(konto)
            r1 = range(int(ke[1][0]),int(ke[1][1])+1)
            r2 = range(int(ke[2][0]),int(ke[2][1])+1)
            return [('code','>=',ke[0][0]),('code','<=',ke[0][1]),('code','not in',' [%s]' % ','.join([str(i) for i in r1 + r2]))]
        if len(kl.findall(konto)) == 2:
            ke = kl.findall(konto)
            r1 = range(int(ke[1][0]),int(ke[1][1])+1)
            return [('code','>=',ke[0][0]),('code','<=',ke[0][1]),('code','not in',' [%s]' % ','.join([str(i) for i in r1]))]
        
        if len(kl.findall(konto)) == 2 and len(k.findall(konto)) > 5:
            raise Warning('hello')
            ke = kl.findall(konto)
            r0 = [str(i) for i in range(int(ke[0][0]),int(ke[0][1])+1)]
            r1 = [str(i) for i in range(int(ke[1][0]),int(ke[1][1])+1)]
            return [('code','in','[%s]' % ','.join(r0)),('code','not in','[%s]' % ','.join(k.findall(konto)[2:6] + r1))]
    
    
    if len(k.findall(konto)) == 1:
        return [('code','=',k.findall(konto)[0])]
    if len(k.findall(konto)) in [3,4]:
        dom = ['|' for i in range(1,len(k.findall(konto)))]
        for ke in k.findall(konto):
            dom.append(('code','=',ke))
        return dom
    
    if len(kl.findall(konto)) == 1:
        ke = kl.findall(konto)[0]
        return ['&',('code','>=',ke[0]),('code','<=',ke[1])] 
    
    if k.findall(konto):
        if len(k.findall(konto)) == 2:
            for i,k in enumerate(k.findall(konto)):
               dom.append(('code',sign[i % 2],k))
    if k_eller.findall(konto):
        ke = k_eller.findall(konto)[0]
        return ['&',('code','>=',ke[0].split('-')[0]),('code','<=',ke[0].split('-')[1]),'|','&',('code','>=',ke[1].split('-')[0]),('code','<=',ke[1].split('-')[1])]    
    if s_eller.findall(konto):
        ke = s_eller.findall(konto)[0]
        return ['|',('code','=',ke[0]),('code','=',ke[1])]
    if k_eller2.findall(konto):
        l = []
        for ke in k_eller2.findall(konto):
            l += range(int(ke[0].split('-')[0]),int(ke[1].split('-')[0])+1)
        return [('code','in','[%s]' % ','.join([str(i) for i in l]))]    
        
         
    k = re.compile('Konto (\d{4}-\d{4}), (\d{4}-\d{4}), (\d{4}-\d{4}) eller (\d{4}-\d{4})')
    if k.findall(konto):
        ke = k.findall(konto)[0]
        r0 = range(int(ke[0].split('-')[0]),int(ke[0].split('-')[1])+1)
        r1 = range(int(ke[1].split('-')[0]),int(ke[1].split('-')[1])+1)
        r2 = range(int(ke[2].split('-')[0]),int(ke[2].split('-')[1])+1)
        r3 = range(int(ke[3].split('-')[0]),int(ke[3].split('-')[1])+1)
        return [('code','in',' [%s]' % ','.join([str(i) for i in r0 + r1 + r2 + r3]))]
    


    if len(dom) == 2:
        l = ['|',dom[0],dom[1]]
        dom = l

    if len(dom) == 3:
        l = ['&',dom[0],dom[1],'|',dom[2]]
        dom = l
    return dom


page = requests.get('https://www.arsredovisning-online.se/bas_kontoplan')
tree = html.fromstring(page.content)

data = tree.xpath('//h3/text()')

konton = tree.xpath('//h4/text()')
texter = tree.xpath('//ul/li/text()')
rubr = tree.xpath('//ul/li/b/text()')

print "    l = ["
t = 2
for i in range(0,len(konton)):
    if konton[i] > 'Konto 3':
        type = 'R'
    else:
        type = 'B'
    falt = texter[t]
    if len(rubr) > t and rubr[t-1] == 'Beskrivning:':
        besk = texter[t+1].strip().replace('"',"'")
        t += 1
    else:
        besk = ''
    if len(domain(konton[i])) == 0:
        raise Warning(konton[i])
    print "        {'t':'%s','f':\"%s\",'b':\"%s\",'k':%s}," % (type,falt.strip(),besk,domain(konton[i]))
    t += 1
    
print "    ]"
