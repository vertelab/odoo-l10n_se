# -*- coding: utf-8 -*-
"""Class to parse camt files."""
##############################################################################
#
#    Copyright (C) 2013-2016 Vertel AB <http://vertel.se>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GMaxNU Affero General Public License as published
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

# git clone -b 8.0 https://github.com/OCA/bank-statement-import.git


import re

record = """01BGMAX               0120160223133624677439P                                   
050057237273          SEK                                                       
20000000000063287                    000000000000120500314906301742600          
26LEDEMIA                                                                       
27RÖDHAKEVÄGEN 16 LENA BLIXT         135 68                                     
28TYRESÖ                                                                        
20000000000064002                    000000000000346125314906300835900          
2564002                                                                         
26KARLSSON, DIANA                                                               
27OLOFSBO SKATTAGÅRDEN 122           311 91                                     
28 FALKENBERG                                                                   
20000000000051601                    000000000000297000314906301211080          
26MIA VILTOK STUDIO AB                                                          
27SANDNÄSETVÄGEN 902                 975 94                                     
28LULEÅ                                                                         
200000000000KUNDNR 4325 FAKTURA 63890000000000000408500314906301211070          
26JENSEN ANGELIE                                                                
27TERRÄNGVÄGEN 105 LGH 1201          129 47                                     
28HÄGERSTEN                                                                     
200000000000Minerva 00040147         000000000000490525314906300269910          
26CECILIA KARLSSON                                                              
27NAUM JUTAGÅRDEN 4                  534 94                                     
28VARA                                                                          
200000000000Faktnr: 63600            000000000000270875314906300269930          
26ZAYNAB EL BAGDADI MAHMOUD                                                     
27ÖSTAKULLAVÄGEN 19                  438 34                                     
28LANDVETTER                                                                    
20000000000056157                    000000000000094250314906300269920          
26LARS-JÖRGEN WIGERTZ                                                           
27FRILLESÅS TRÄDGÅRDSVÄG 6 C         439 62                                     
28FRILLESÅS                                                                     
200000000000fakturanr 63313 kund 870 000000000000368675314906301538320          
26WALLIN, YVONNE                                                                
27TIMMERVÄGEN 5                      737 49                                     
28FAGERSTA                                                                      
20000000000064317                    000000000000211240314906301413160          
26SKOOG, ITA                                                                    
27DAMASTGATAN 52                     507 34                                     
28BRÄMHULT                                                                      
20000000000063778                    000000000000390850314906301413150          
26SKOOG, ITA                                                                    
27DAMASTGATAN 52                     507 34                                     
28BRÄMHULT                                                                      
20000000000064707                    000000000000206250314906301413170          
26SKOOG, ITA                                                                    
27DAMASTGATAN 52                     507 34                                     
28BRÄMHULT                                                                      
20000000000062742                    000000000001405875314906301658880          
26RUM FÖR HÄLSA I TYRESÖ HB                                                     
27TYRESÖ SLOTT, SLOTTET              135 60                                     
28TYRESÖ                                                                        
20000000000062775                    000000000001100265314906301658870          
26RUM FÖR HÄLSA I TYRESÖ HB                                                     
27TYRESÖ SLOTT, SLOTTET              135 60                                     
28TYRESÖ                                                                        
20000000000062185                    000000000000344000314906301658860          
26RUM FÖR HÄLSA I TYRESÖ HB                                                     
27TYRESÖ SLOTT, SLOTTET              135 60                                     
28TYRESÖ                                                                        
20000000000063687                    000000000000311175314906301742590          
26JENNY ANDERSSON                                                               
27SILA MARIEDAL 110                  610 14                                     
28REJMYRE                                                                       
15000000000000000000081050090427838532016022300070000000000006366105SEK00000015 
050057237273          SEK                                                       
200000000000Faktnr 61599             000000000000822915314906302869730          
26ESMERALDA FOGEL                                                               
27TRÖINGEVÄGEN 36                    311 37                                     
28FALKENBERG                                                                    
200000000000faktura: 63701           000000000000201028314906302869740          
26EMMA HEDBORG                                                                  
27KLOSTERGATAN 4 LGH 1402            703 61                                     
28ÖREBRO                                                                        
20000351299362937                    000000000000697817324906302412380          
2500035508                                                                      
26Nyhetsbolaget Sverige AB           Tegeluddsvägen 3-5                         
27                                   11579                                      
28STOCKHOLM                                                                     
29005562736032                                                                  
20005349293061571                    000000000001908050324906302052640          
26M&M Company AB                     Gundas Gata 60                             
27                                   43151                                      
28MÖLNDAL                                                                       
29005567621130                                                                  
20005630293860939                    000000000000419375324906302272730          
26THOMAS COOK NORTHERN EUROPE AB                                                
27                                   10520                                      
28STOCKHOLM                                                                     
29005560419862                                                                  
20005630293853827                    000000000000819100324906302272720          
26THOMAS COOK NORTHERN EUROPE AB                                                
27                                   10520                                      
28STOCKHOLM                                                                     
29005560419862                                                                  
20005630293857538                    000000000000239750324906302272710          
26THOMAS COOK NORTHERN EUROPE AB                                                
27                                   10520                                      
28STOCKHOLM                                                                     
29005560419862                                                                  
15000000000000000000081050090427838532016022300071000000000005108035SEK00000007 
7000000022000000000000000000000002
"""

class CobolParser(object):
    """Parser for BgMax bank statement import files."""
    
    layout = {
            '01': [ # Start post
                ('layoutnamn',3,22),
                ('version',23,24),
                ('skrivdag',25,44),
                ('testmarkering',45,45),
                ('reserv',46,80),
            ],
            '05': [ # Record start
                ('mottagarbankgiro',3,12),
                ('mottagarplusgiro',13,22),
                ('valuta',46,50),
            ],
            '15': [ # Record end / insättning
                ('mottagarbankkonto',3,37),
                ('betalningsdag',38,45),
                ('inslopnummer',46,50),
                ('insbelopp',51,68),
                ('valuta',69,71),
                ('antal_bet',72,79),
                ('typ_av_ins',80,80),
            ],
            '20': [ # betalning
                ('bankgiro',3,12),
                ('referens',13,37),
                ('betbelopp',38,55),
                ('referenskod',56,56),
                ('betalningskanalkod',57,57),
                ('BGC-nummer',58,69),
                ('avibildmarkering',70,70),
                ('reserv',71,80),
            ],
            '21': [ # avdrag
                ('bankgiro',3,12),
                ('referens',13,37),
                ('betbelopp',38,55),
                ('referenskod',56,56),
                ('betalningskanalkod',57,57),
                ('BGC-nummer',58,69),
                ('avibildmarkering',70,70),
                ('avdragskod',71,71),
            ],
            '22': [ 
                ('22bankgiro',3,12),
                ('22referens',13,37),
                ('22betbelopp',38,55),
                ('22referenskod',56,56),
                ('22betalningskanalkod',57,57),
                ('22BGC-nummer',58,69),
                ('22avibildmarkering',70,70),
                ('22reserv',71,80),
            ],
            '23': [ 
                ('23bankgiro',3,12),
                ('23referens',13,37),
                ('23betbelopp',38,55),
                ('23referenskod',56,56),
                ('23betalningskanalkod',57,57),
                ('23BGC-nummer',58,69),
                ('23avibildmarkering',70,70),
                ('reserv',71,80),
            ],
            '25': [ 
                ('informationstext',3,52),
                ('reserv',53,80),
            ],            
            '26': [ 
                ('betalarens_namn',3,37),
                ('extra_namn',38,72),
                ('reserv',73,80),
            ],
            '27': [ 
                ('betalarens_adress',3,37),
                ('betalarens_postnr',38,46),
                ('reserv',47,80),
            ],
            '28': [ 
                ('betalarens_ort',3,37),
                ('betalarens_land',38,72),
                ('betalarens_landkod',73,74),
                ('reserv',75,80),
            ],
            '29': [ 
                ('organisationsnummer',3,14),
                ('reserv',15,80),
            ],
            '70': [ 
                ('antal_betposter',3,10),
                ('antal_avdrag',11,18),
                ('antal_ref',19,26),
                ('antal_ins',27,34),
                ('reserv',35,80),
            ],

        }

    def parse_row(self,row):
        record = {'type': row[0:2]}
        for name,start,stop in self.layout[record['type']]:
            record[name] = row[start-1:stop]
        return record

    def parse(self,data):
        pass
        
            
class avs():
    def __init__(self,rec):
        self.header = rec
        self.footer = {}
        self.ins = []
        self.bet = []
        self.type = ''

    def add(self,rec):
        self.type = rec['type']
        if rec['type'] == '20':
            self.type = '20'
            self.ins.append(rec)
        elif rec['type'] == '21':
            self.type = '21'
            self.bet.append(rec)
        elif self.type == '20':
            for r in rec.keys():
                self.bet[-1][r] = rec[r]
        elif self.type == '21':
            for r in rec.keys():
                self.ins[-1][r] = rec[r]
            
    def check_insbelopp(self):
        #print "summa",sum([float(b['betbelopp'])/100 for b in self.ins])
        #print "insbel",float(self.footer['insbelopp']) / 100
        return float(self.footer['insbelopp']) / 100 == sum([float(b['betbelopp'])/100 for b in self.ins])
    def check_antal_bet(self):
        #print "antal",len(self.ins)
        #print "antal_bet",int(self.footer['antal_bet'])
        return len(self.ins) == int(self.footer['antal_bet'])
    
            #~ '15': [ # Record end / insättning
                #~ ('mottagarbankkonto',3,37),
                #~ ('betalningsdag',38,45),
                #~ ('inslopnummer',46,50),
                #~ ('insbelopp',51,68),
                #~ ('valuta',69,71),
                #~ ('antal_bet',72,79),
                #~ ('typ_av_ins',80,80),    
    
                        
class bgmax(CobolParser):
    def __init__(self, data):
        self.row = 0
        self.data = data.splitlines()
        self.rows = len(self.data)
        self.header = {}
        self.footer = {}
        self.avsnitt = []
    
    def __iter__(self):
        return self

    def next(self):
        if self.row >= self.rows:
            raise StopIteration
        rec = self.next_rec()
        if rec['type'] == '01':
            self.header = rec
            rec = self.next_rec()
        if rec['type'] == '70':
            self.footer = rec
            raise StopIteration()
        if rec['type'] == '05':
            self.avsnitt.append(avs(rec))
            rec = self.next_rec()
            while rec['type'] in ['20','21','22','23','25','26','27','28','29']:
                self.avsnitt[-1].add(rec)
                rec = self.next_rec()                
            if rec['type'] == '15':
                self.avsnitt[-1].footer = rec
            return self.avsnitt[-1]
        return rec

    def next_rec(self):
        self.row += 1
        return self.parse_row(self.data[self.row])
    def check_avsnitt(self):
        ok = True
        for a in self.avsnitt:
            if not (a.check_insbelopp() and a.check_antal_bet()):
                ok = False
        return ok
    def check_antal_ins(self):
        #print "antal",len(self.avsnitt)
        #print "antal_ins",int(self.footer['antal_ins'])
        return len(self.avsnitt) == int(self.footer['antal_ins'])
    def check_antal_betposter(self):
        #print "antal",sum([len(a.ins) for a in self.avsnitt])
        #print "antal_betposter",int(self.footer['antal_betposter'])
        return sum([len(a.ins) for a in self.avsnitt]) == int(self.footer['antal_betposter'])
    def check(self):
        ok = True
        for c,result in [('avsnitt',self.check_avsnitt()),('antal_betpost',self.check_antal_betposter()),('check_antal_ins',self.check_antal_ins())]:
            if not result:
                print "Error in check %s" % c
                ok = False
        return ok


a = bgmax(record)


for av in a:
    print "ins",av.header,av.footer

print a.check()
