#!/usr/bin/python
# coding: utf8
import csv
kplan = csv.reader(open('Kontoplan_K1_2015_ver1_alla.csv', 'rb'), delimiter=';', quotechar='"')


class label():
  labels = {}
  def out(self,str):
    if(not self.labels.has_key(str)):
      print str
      self.labels[str]=True
      
label()  

l = label()


print """id,code,name,parent_id:id,type,user_type:id,reconcile,"tax_ids:id","chart_template_id:id"
K1,a0,Företaget,,view,account.data_account_type_view,,,"""


for row in kplan:
    code = int(row[0])
    if(code in range(1000,1010)):
        l.out( 'k1_1,1,Balansräkning,K1,view,account.data_account_type_view,,,l10n_se.a')
        l.out( 'k1_10,1 TA,Anläggningstillgångar,k1_1,view,account.data_account_type_view,,,l10n_se.a')
        l.out('B1k1,B1,Immateriella anläggningstillgångar,k1_10,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","B1k1","other","account.data_account_type_asset","false",,l10n_se.a' % (row[0],code,row[1])
    if(code in range(1110,1120)):     
        l.out('B2k1,B2,Byggnader och mark,k1_10,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","B2k1","other","account.data_account_type_asset","false",,l10n_se.a' % (row[0],code,row[1])
    if(code  in range(1120,1200)):
        l.out('B3k1,B3,Mark och andra tillgångar som inte får skrivas av,k1_10,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s",B3k1,other,account.data_account_type_asset,false,,l10n_se.a' % (row[0],code,row[1])
    if(code in range(1220,1230)):
        l.out('B4k1,B4,Maskiner och inventarier,k1_10,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","B4k1","other","account.data_account_type_asset","false",aI,l10n_se.a' % (row[0],code,row[1])
    if(code in range(1230,1400)):                                           
        l.out('B5k1,B5,Övriga anläggningstillgångar,k1_10,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","B5k1","other","account.data_account_type_asset","false",,l10n_se.a' % (row[0],code,row[1])
        
    if(code in range(1400,1500)):                                           
        l.out('k1_14,1 TO,Omsättningstillgångar,k1_1,view,account.data_account_type_view,,,l10n_se.a')
        l.out('B6k1,B6,Lager och pågående arb,k1_14,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","B6k1","other","account.data_account_type_asset","false",,l10n_se.a' % (row[0],code,row[1])
    if(code in range(1500,1600)):
        l.out('B7k1,B7,Kundfordringar,k1_14,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","B7k1","receivable","account.data_account_type_receivable","true",,l10n_se.a' % (row[0],code,row[1])
    if(code in range(1600,1900)):
        l.out('B8k1,B8,Övriga fordringar,k1_14,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","B8k1","other","account.data_account_type_asset","false",,l10n_se.a' % (row[0],code,row[1])
    if(code in range(1900,2000)):                                           
        l.out('B9k1,B9,Kassa och bank,k1_14,view,account.data_account_type_view,,,l10n_se.a')
    if(code in range(1900,1920)):                                           
        print 'k1_%s,%d,"%s","B9k1","liquidity","account.data_account_type_cash","false",,l10n_se.a' % (row[0],code,row[1])
    if(code in range(1920,1930)):                                           
        print 'k1_%s,%d,"%s","B9k1","liquidity","account.data_account_type_bank","false",,l10n_se.a' % (row[0],code,row[1])
    if(code in range(1930,2000)):                                           
        print 'k1_%s,%d,"%s","B9k1","liquidity","account.data_account_type_bank","false",,l10n_se.a' % (row[0],code,row[1])


    if(code in (range(2010,2020))):    #  +range(2050,2060)                                        
        l.out('k1_2,2 S,Eget kapital och skulder,k1_1,view,account.data_account_type_view,,,l10n_se.a')
        l.out('B10k1,B10,Eget kapital,k1_2,view,account.data_account_type_view,,,l10n_se.a')
#        print 'k1_%s,%d,"%s","B10k1","other","account.conf_account_type_equity","false",,l10n_se.a' % (row[0],code,row[1])
        print 'k1_%s,%d,"%s","B10k1","other","account.data_account_type_liability","false",,l10n_se.a' % (row[0],code,row[1])
    if(code in range(2100,2200)):
        l.out('B11k1,B11,Obeskattade reserver,k1_2,view,account.data_account_type_view,,,l10n_se.a')
#        print 'k1_%s,%d,"%s","B11k1","other","account.conf_account_type_equity","false",,l10n_se.a' % (row[0],code,row[1])
        print 'k1_%s,%d,"%s","B11k1","other","account.data_account_type_liability","false",,l10n_se.a' % (row[0],code,row[1])
    if(code in range(2200,2300)):
        l.out('B12k1,B12,Avsättningar,k1_2,view,account.data_account_type_view,,,l10n_se.a')
#        print 'k1_%s,%d,"%s","B12k1","other","account.conf_account_type_equity","false",,l10n_se.a' % (row[0],code,row[1])
        print 'k1_%s,%d,"%s","B12k1","other","account.data_account_type_liability","false",,l10n_se.a' % (row[0],code,row[1])
    if(code in (range(2300,2400)+range(2410,2420)+range(2480,2490))):
        l.out('B13k1,B13,Skulder,k1_2,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","B13k1","other","account.data_account_type_liability","false",,l10n_se.a' % (row[0],code,row[1])
    if(code in range(2500,2600)+range(2600,2700)+range(2710,2720)+range(2730,2740)):
        l.out('B14k1,B14,Skatteskulder,k1_2,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","B14k1","other","account.data_account_type_liability","false",,l10n_se.a' % (row[0],code,row[1])
    if((code in range(2440,2480)) and (code not in range(2450,2460))):
        l.out('B15k1,B15,Leverantörsskulder,k1_2,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","B15k1","payable","account.data_account_type_payable","true",aI,l10n_se.a' % (row[0],code,row[1])
    if(code in (range(2420,2440)+range(2450,2460)+range(2490,2500)+range(2700,3000))) and (code not in (range(2710,2720)+range(2730,2739))):
        l.out('B16k1,B16,Övriga skulder,k1_2,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","B16k1","other","account.data_account_type_liability","false",,l10n_se.a' % (row[0],code,row[1])

    if(code in range(3000,3100)):
        l.out('k1_3,3,Resultaträkning,K1,view,account.data_account_type_view,,,l10n_se.a')
        l.out('k1_30,I,Intäkter,k1_3,view,account.data_account_type_view,,,l10n_se.a')
        l.out('R1k1,R1,"Försäljning och utfört arbete samt övriga momspliktiga intäkter",k1_30,view,account.data_account_type_income,,,l10n_se.a')
        print 'k1_%s,%d,"%s","R1k1","other","account.data_account_type_income","false",aMP1,l10n_se.a' % (row[0],code,row[1])
    if(code in range(3100,3200)):
        l.out('R2k1,R2,Momsfria intäkter,k1_30,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","R2k1","other","account.data_account_type_income","false",aMF,l10n_se.a' % (row[0],code,row[1])
    if(code in range(3200,3300)):
        l.out('R3k1,R3,Bil och bosradsförmån,k1_30,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","R3k1","other","account.data_account_type_income","false",,l10n_se.a' % (row[0],code,row[1])
    if(code == 8310):
        l.out('R4k1,R4,Ränteintäkter mm,k1_30,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","R4k1","other","account.data_account_type_income","false",,l10n_se.a' % (row[0],code,row[1])
    if(code in range(4000,5000)): 
        l.out('k1_40,K,Kostnader,k1_3,view,account.data_account_type_view,,,l10n_se.a')
        l.out('R5k1,R5,"Varor, material och tjänster",k1_40,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","R5k1","other","account.data_account_type_expense","false",aI,l10n_se.a' % (row[0],code,row[1])
    if(code in range(5000,7000)): 
        l.out('R6k1,R6,Övriga externa kostnader,k1_40,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","R6k1","other","account.data_account_type_expense","false",aI,l10n_se.a' % (row[0],code,row[1])
        
    if(code in (range(7720,7730)+range(7770,7780)+range(7820,7830)+range(8850,8855))):
        l.out('k1_7,7,Avskrivningar,K1,view,account.data_account_type_view,,,l10n_se.a')

        
    if(code in range(7000,7700)):
        l.out('R7k1,R7,Anställd personal,k1_40,view,account.data_account_type_view,,,l10n_se.a')      
        print 'k1_%s,%d,"%s","R7k1","other","account.data_account_type_expense","false",,l10n_se.a' % (row[0],code,row[1])
    if(code == 8410):
        l.out('R8k1,R8,Räntekostnader mm,k1_40,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","R8k1","other","account.data_account_type_expense","false",,l10n_se.a' % (row[0],code,row[1])
        
    if(code in range(7710,7820)):  # This has to come before R10
        l.out('k1_7,7,Avskrivningar,K1,view,account.data_account_type_view,,,l10n_se.a')

    if(code in (range(7720,7730)+range(7770,7780)+range(7820,7830)+range(8850,8855))):
        l.out('k1_7,7,Avskrivningar,K1,view,account.data_account_type_view,,,l10n_se.a')
        l.out('R9k1,R9,Avskrivningar och nedskrivningar byggnader och markanläggningar,k1_7,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","R9k1","other","account.data_account_type_expense","false",,l10n_se.a' % (row[0],code,row[1])
    if(code in (range(7710,7720)+range(7730,7740)+range(7760,7770)+range(7780,7790)+range(7810,7820)+range(7830,7840)+range(8856,8860))):
        l.out('R10k1,R10,Avskrivningar och nedskrivningar maskiner och inventarier och immateriella tillgångar,k1_7,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","R10k1","other","account.data_account_type_expense","false",,l10n_se.a' % (row[0],code,row[1])
    if(code in range(8990,9000)):
        l.out('k1_8,8,Årets resultat,K1,view,account.data_account_type_view,,,l10n_se.a')
        l.out('R11k1,R11,Bokfört resultat,k1_8,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","R11k1","other","account.data_account_type_expense","false",,l10n_se.a' % (row[0],code,row[1])


    if(code in range(2050,2090)):  # This has to come before U2
        l.out('k1_9,U,Upplysningar,K1,view,account.data_account_type_view,,,l10n_se.a')


    if(code in range(2080,2090)):
        l.out('k1_9,U,Upplysningar,K1,view,account.data_account_type_view,,,l10n_se.a')
        l.out('U1k1,U1,Periodiseringsfonder,k1_9,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","U1k1","other","account.data_account_type_asset","false",,l10n_se.a' % (row[0],code,row[1])
    if(code in range(2050,2060)):
        l.out('U2k1,U2,Expansionsfond,k1_9,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","U2k1","other","account.data_account_type_asset","false",,l10n_se.a' % (row[0],code,row[1])
    if(code in range(2060,2070)):
        l.out('U3k1,U3,Ersättningsfonder,k1_9,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","U3k1","other","account.data_account_type_asset","false",,l10n_se.a' % (row[0],code,row[1])
    if(code in range(2070,2080)):
        l.out('U4k1,U4,"Insatsemissioner, skogskonto, upphovsmannakonto, avbetalningsplan på skog od",k1_9,view,account.data_account_type_view,,,l10n_se.a')
        print 'k1_%s,%d,"%s","U4k1","other","account.data_account_type_asset","false",,l10n_se.a' % (row[0],code,row[1])
