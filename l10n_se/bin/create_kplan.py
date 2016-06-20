#!/usr/bin/python
# coding: utf8
import csv
kplan = csv.reader(open('Kontoplan_Normal_2015_alla.csv', 'rb'), delimiter=';', quotechar='"')

print """id,code,name,parent_id:id,type,user_type:id,reconcile
SE0,0,Företaget,,view,account_type_view,"""

class label():
  labels = {}
  def out(self,str):
    if(not self.labels.has_key(str)):
      print str
      self.labels[str]=True
      
label()  

l = label()

for row in kplan:
    code = int(row[0])
    if(code in range(1000,1100)):
        l.out( 'chart_1,1,Balansräkning,SE0,view,account_type_income_view1,')
        l.out( 'chart_10,10,Anläggningstillgångar,chart_1,view,account_type_fixed_assets,')
        l.out('B1,100,Immateriella anläggningstillgångar,chart_10,view,account_type_fixed_assets,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"B1","view","account_type_income_view1","false")
    if((code in range(1100,1200)) and (code not in (1130,1140,1150))):     
        l.out('B2,110,Byggnader och mark,chart_10,view,account_type_fixed_assets,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"B2","view","account_type_income_view1","false")
    if(code in (1130,1140,1180,1291)):
        l.out('B3,11,Mark och andra tillgångar som inte får skrivas av,chart_10,view,account_type_fixed_assets,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"B3","view","account_type_income_view1","false")
    if(code in range(1200,1300) and (code != 1291)):
        l.out('B4,12,Maskiner och inventarier,chart_10,view,account_type_fixed_assets,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"B4","view","account_type_income_view1","false")
    if(code in range(1300,1400)):                                           
        l.out('B5,13,Finansiella anläggningstillgångar,chart_10,view,account_type_fixed_assets,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"B5","view","account_type_income_view1","false")
        

    if(code in range(1400,1500)):                                           
        l.out('chart_14,14,Omsättningstillgångar,chart_1,view,account_type_current_assets,')
        l.out('B6,140,Lager och pågående arb,chart_14,view,account_type_current_assets,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"B6","view","account_type_income_view1","false")
    if(code in range(1500,1600)):
        l.out('B7,15,Kundfordringar,chart_10,view,account_type_current_assets,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"B7","view","account_type_income_view1","false")
    if(code in range(1600,1900)):
        #chart_17,17,Förutbetalda kostnader och upplupna intäkter,chart_14,view,account_type_current_assets,
        l.out('B8,16,Övriga kortfristiga fordringar,chart_14,view,account_type_current_assets,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"B8","view","account_type_income_view1","false")
    if(code in range(1900,2000)):                                           
        l.out('B9,19,Kassa och bank,chart_14,view,account_type_current_assets,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"B9","view","account_type_income_view1","false")


    if(code in (range(2010,2020)+range(2050,2060))):                                              
        l.out('chart_2,2,Eget kapital och skulder,chart_1,view,account_type_current_liabilities,')
        l.out('B10,20,Eget kapital,chart_2,view,account_type_current_liabilities,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"B10","view","account_type_income_view1","false")
    if(code in range(2100,2200)):
        l.out('B11,21,Obeskattade reserver,chart_2,view,account_type_current_liabilities,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"B11","view","account_type_income_view1","false")
    if(code in range(2200,2300)):
        l.out('B12,22,Avsättningar,chart_2,view,account_type_current_liabilities,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"B12","view","account_type_income_view1","false")
    if(code in (range(2300,2400)+range(2410,2420)+range(2480,2490))):
        l.out('B3,23,Skulder,chart_2,view,account_type_current_liabilities,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"B13","view","account_type_income_view1","false")
    if(code in range(2500,2600)+range(2600,2700)+range(2710,2720)+range(2730,2740)):
        l.out('B14,25,Skatteskulder,chart_2,view,account_type_income_view1,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"B14","view","account_type_income_view1","false")
    if((code in range(2440,2480)) and (code not in range(2450,2460))):
        l.out('B15,26,Moms och särskilda punktskatter,chart_2,view,account_type_income_view1,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"B15","view","account_type_income_view1","false")
    if(code in (range(2420,2440)+range(2450,2460)+range(2490,2500)+range(2700,3000))) and (code not in (range(2710,2720)+range(2730,2739))):
        l.out('B16,27,Personalens skatter  avg.och löneavdrag,chart_2,view,account_type_income_view1,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"B16","view","account_type_income_view1","false")

    if(code in range(3000,3100)):
        l.out('chart_3,3,Resultaträkning,SE0,view,account_type_current_assets_view1,')
        l.out('chart_30,30,Intäkter,chart_3,view,account_type_current_assets_view1,')
        l.out('R1,31,"Försäljning och utfört arbete samt övriga momspliktiga intäkter",chart_30,view,account_type_income_view1,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"R1","view","account_type_income_view1","false")
    if(code in range(3100,3200)):
        l.out('R2,32,Momsfria intäkter,chart_30,view,account_type_current_assets_view1,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"R2","view","account_type_income_view1","false")
    if(code in range(3200,3300)):
        l.out('R3,33,Bil och bosradsförmån,chart_30,view,account_type_current_assets_view1,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"R3","view","account_type_income_view1","false")
    if(code == 8310):
        l.out('R4,34,Ränteintäkter mm,chart_30,view,account_type_current_assets_view1,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"R4","view","account_type_income_view1","false")
    if(code in range(4000,5000)): 
        l.out('chart_40,40,Kostnader,chart_3,view,account_type_current_assets_view1,')
        l.out('R5,45,Varor och legoarbeten,chart_40,view,account_type_current_assets_view1,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"R5","view","account_type_income_view1","false")
    if(code in range(5000,7000)): 
        l.out('R6,46,Varor och legoarbeten,chart_40,view,account_type_current_assets_view1,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"R6","view","account_type_income_view1","false")
    if(code in range(7000,7700)):
        l.out('R7,47,Anställd personal,chart_40,view,account_type_current_assets_view1,')      
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"R7","view","account_type_income_view1","false")
    if(code == 8410):
        l.out('R8,48,Räntekostnader mm,chart_40,view,account_type_current_assets_view1,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"R8","view","account_type_income_view1","false")
    if(code in (range(7720,7730)+range(7770,7780)+range(7820,7830)+range(8850,8855))):
        l.out('chart_7,7,Avskrivningar,SE0,view,account_type_current_assets_view1,')
        l.out('R9,49,Avskrivningar och nedskrivningar byggnader och markanläggningar,chart_7,view,account_type_current_assets_view1,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"R9","view","account_type_income_view1","false")
    if(code in (range(7710,7720)+range(7730,7740)+range(7760,7770)+range(7780,7790)+range(7810,7820)+range(7830,7840)+range(8856,8860))):
        l.out('R10,50,Avskrivningar och nedskrivningar maskiner och inventarier och immateriella tillgångar,chart_7,view,account_type_current_assets_view1,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"R10","view","account_type_income_view1","false")
    if(code in range(8990,9000)):
        l.out('chart_8,8,Årets resultat,SE0,view,account_type_current_assets_view1,')
        l.out('R11,51,Bokfört resultat,chart_8,view,account_type_current_assets_view1,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"R11","view","account_type_income_view1","false")

    if(code in range(2080,2090)):
        l.out('chart_9,9,Upplysningar,SE0,view,account_type_current_assets_view1,')
        l.out('U1,91,Periodiseringsfonder,chart_9,view,account_type_current_assets_view1,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"U1","view","account_type_income_view1","false")
    if(code in range(2050,2060)):
        l.out('U2,92,Expansionsfond,chart_9,view,account_type_current_assets_view1,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"U2","view","account_type_income_view1","false")
    if(code in range(2060,2070)):
        l.out('U3,93,Ersättningsfonder,chart_9,view,account_type_current_assets_view1,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"U3","view","account_type_income_view1","false")
    if(code in range(2070,2080)):
        l.out('U4,94,"Insatsemissioner, skogskonto, upphovsmannakonto, avbetalningsplan på skog od",chart_9,view,account_type_current_assets_view1,')
        print 'chart_%s,%d,"%s",%s,%s,%s,%s' % (row[0],code,row[1],"U4","view","account_type_income_view1","false")


