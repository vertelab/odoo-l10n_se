#!/usr/bin/python
# coding: utf8
import csv
kplan = csv.reader(open('Kontoplan_Normal_2015_alla.csv', 'rb'), delimiter=';', quotechar='"')


class label():
  labels = {}
  def out(self,str):
    if(not self.labels.has_key(str)):
      print str
      self.labels[str]=True
      
label()  

l = label()


print 'id,code,name,parent_id:id,type,user_type:id,reconcile,"tax_ids:id","chart_template_id:id"'
print "K2,b0,Företaget K2,,view,account.data_account_type_view,,,"


for row in kplan:
    code = int(row[0])
    
# BALANSRÄKNING
# Tillgångar


# Anläggningstillgångar

# Immatriella anläggningstillgångar
    
    if(code == 1088): # excl 1088
        l.out('22k2,2.2,Förskott avseende immateriella anläggningstillgångar,k2_10,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","22k2","other","account.data_account_type_asset","false",,l10n_se.b' % (row[0],code,row[1])
        
        
    if(code in range(1000,1100) and not code == 1088): # 10xx exkl 1088
        l.out('k2_1,2,Balansräkning,K2,view,account.data_account_type_view,,,l10n_se.b')
        l.out('k2_10,2 AT,Anläggningstillgångar,k2_1,view,account.data_account_type_view,,,l10n_se.b')
        l.out('21k2,2 IAT,Immateriella anläggningstillgångar,k2_10,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","21k2","other","account.data_account_type_asset","false",,l10n_se.b' % (row[0],code,row[1])

# Materiella anläggningstillgångar

    if(code in range(1120,1130)):  # 112x
        l.out('25k2,2.5,Förbättringsutgifter på annans fastighet,k2_10,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","25k2","other","account.data_account_type_asset","false",bI,l10n_se.b' % (row[0],code,row[1])

    if(code in range(1180,1190)+range(1280,1290)):  # 118x och 128x
        l.out('26k2,2.6,Pågående nyanläggningar och förskott avseende materiella anläggningstillgångar,k2_10,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","26k2","other","account.data_account_type_asset","false",bI,l10n_se.b' % (row[0],code,row[1])


    if(code in range(1100,1200) and not (code in range(1180,1190) or code in range(1120,1130))):  # 11xx  exkl 112x/118x
        l.out('23k2a,2 MAT,Materiella anläggningstillgångar,k2_10,view,account.data_account_type_view,,,l10n_se.b')
        l.out('23k2,2.3,Byggnader och mark,23k2a,view,account.data_account_type_view,,bI,l10n_se.b')
        print 'k2_%s,%d,"%s","23k2","other","account.data_account_type_asset","false",bI,l10n_se.b' % (row[0],code,row[1])

    if(code in range(1200,1300) and not code in range(1280,1290)):  # 12xx  exkl 128x
        l.out('24k2,2.4,Byggnader och mark,k2_10,view,account.data_account_type_view,,bI,l10n_se.b')
        print 'k2_%s,%d,"%s","24k2","other","account.data_account_type_asset","false",bI,l10n_se.b' % (row[0],code,row[1])

# Finansiella anläggningstillgångar

    if(code in range(1300,1320)):                                           
        l.out('k2_10a,2 FAT,Finansiella anläggningstillgångar,k2_10,view,account.data_account_type_view,,,l10n_se.b')
        l.out('27k2,2.7,Andelar i koncernföretag,k2_10a,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","27k2","other","account.data_account_type_asset","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(1320,1330)+range(1340,1350)):                                           
        l.out('29k2,2.9,Fordringar hos koncern- och intresseföretag,k2_10a,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","29k2","other","account.data_account_type_asset","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(1330,1340)):                                           
        l.out('28k2,2.8,Andelar i intresseföretag,k2_10a,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","28k2","other","account.data_account_type_asset","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(1350,1360)):                                           
        l.out('210k2,2.10,Andra långfristiga värdepappersinnehav,k2_10a,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","210k2","other","account.data_account_type_asset","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(1360,1370)):                                           
        l.out('211ak2,2.11,Lån till delägare eller närstående,k2_10a,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","211ak2","other","account.data_account_type_asset","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(1370,1380)+range(1380,1390)):                                       
        l.out('211bk2,2.11b,Andra långfristiga fordringar,k2_10a,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","211bk2","other","account.data_account_type_asset","false",,l10n_se.b' % (row[0],code,row[1])
                
# Omsättningstillgångar
        
# Varulager
    if(code in range(1410,1420)+range(1420,1430) or code == 1430 or code == 1431 or code == 1438):                                           
        l.out('k2_14a,2 OT,Omsättningstillgångar,k2_1,view,account.data_account_type_view,,,l10n_se.b')
        l.out('k2_14,2 VL,Varulager,k2_1,view,account.data_account_type_view,,,l10n_se.b')
        l.out('213k2,2.13,Råvaror och förnödenheter,k2_14,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","213k2","other","account.data_account_type_asset","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(1440,1450) or code == 1432 or code == 1439):
        l.out('214k2,2.14,Varor under tillverkning,k2_14,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","214k2","receivable","account.data_account_type_receivable","true",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(1450,1460)+range(1460,1470)):
        l.out('215k2,2.15,Färdiga varor och handelsvaror,k2_14,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","215k2","receivable","account.data_account_type_receivable","true",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(1490,1500)):
        l.out('216k2,2.16,Övriga lagertillgångar,k2_14,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","216k2","receivable","account.data_account_type_receivable","true",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(1470,1480)):
        l.out('217k2,2.17,Pågående arbeten för annans räkning,k2_14,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","217k2","receivable","account.data_account_type_receivable","true",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(1480,1490)):
        l.out('218k2,2.18,Förskott till leverantörer,k2_14,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","218k2","receivable","account.data_account_type_receivable","true",,l10n_se.b' % (row[0],code,row[1])
        
# Kortfristiga fordringar        
    if(code in range(1510,1560)+range(1580,1590)):
        l.out('k2_15,15 KF,Kortfristiga fordringar,k2_14a,view,account.data_account_type_view,,,l10n_se.b')
        l.out('219k2,2.19,Kundfordringar,k2_15,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","219k2","receivable","account.data_account_type_receivable","true",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(1560,1580)+range(1660,1670)+range(1670,1680)):
        l.out('220k2,2.20,Fordringar hos koncern- och intresseföretag,k2_15,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","220k2","receivable","account.data_account_type_receivable","true",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(1610,1620)+range(1630,1660)+range(1680,1700)):
        l.out('221k2,2.21,Övriga fordringar,k2_15,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","221k2","receivable","account.data_account_type_receivable","true",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(1620,1630)):
        l.out('222k2,2.22,Upparbetad men ej fakturerad intäkt,k2_15,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","222k2","receivable","account.data_account_type_receivable","true",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(1700,1800)):
        l.out('223k2,2.23,Förutbetalda kostnader och upplupna intäkter,k2_15,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","223k2","receivable","account.data_account_type_receivable","true",,l10n_se.b' % (row[0],code,row[1])
        
# Kortfristiga placeringar        
    if(code in range(1860,1870)):
        l.out('224k2,2.24,Andelar i koncernföretag,k2_18,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","224k2","other","account.data_account_type_asset","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(1800,1900) and not code in range(1860,1870)):
        l.out('k2_18,18 KF,Kortfristiga fordringar,k2_14a,view,account.data_account_type_view,,,l10n_se.b')
        l.out('225k2,2.25,Övrigfa kortfristiga fordringar,k2_18,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","225k2","other","account.data_account_type_asset","false",,l10n_se.b' % (row[0],code,row[1])

# Kassa och bank
        
    if(code in range(1900,2000)):
        l.out('k2_19,19 KB,Kassa och bank,k2_14a,view,account.data_account_type_view,,,l10n_se.b')                                                   
        l.out('226k2,2.26,Kassa och bank,k2_19,view,account.data_account_type_view,,,l10n_se.b')
    if(code in range(1900,1920)):                                           
        print 'k2_%s,%d,"%s","226k2","liquidity","account.data_account_type_cash","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(1920,1930)):                                           
        print 'k2_%s,%d,"%s","226k2","liquidity","account.data_account_type_bank","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(1930,2000)):                                           
        print 'k2_%s,%d,"%s","226k2","liquidity","account.data_account_type_bank","false",,l10n_se.b' % (row[0],code,row[1])

# Eget kapital och skulder

    if(code in range(20,30)):
        l.out('k2_2a,2 ES,Eget kapital och skulder,k2_1,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%sK,%d,"%s","228k2","view","account.data_account_type_view","false",,l10n_se.b' % (row[0],code,row[1])
        
# eget kapital

    if(code in (range(2080,2090))):                                          
        l.out('k2_2,2 S1,Eget kapital och skulder,k2_1,view,account.data_account_type_view,,,l10n_se.b')
        l.out('227k2,EQ,Eget kapital,k2_2,view,account.data_account_type_view,,,l10n_se.b')
        l.out('227ak2,2.27,Bundet eget kapital,k2_2,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","227ak2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in (range(2090,2100))):                                          
        l.out('228k2,2.28,Fritt eget kapital,k2_2,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","228k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])
        
# Obeskattade reserver och avsättningar

# Obeskattade reserver
    if(code in range(2110,2130)):                                          
        l.out('k2_21,2 SRA,Obeskattade reserver och avsättningar,k2_2,view,account.data_account_type_view,,,l10n_se.b')
        l.out('k2_211,2 SR,Obeskattade reserver,k2_21,view,account.data_account_type_view,,,l10n_se.b')
        l.out('229k2,2.29,Periodiseringsfonder,k2_211,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","229k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(2150,2160)):
        l.out('230k2,2.30,Ackumulerade öresavrundningar,k2_211,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","230k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(2160,2200)):
        l.out('231k2,2.31,Övriga obeskattade reserver,k2_211,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","231k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])
        
# Avsättningar
        
    if(code in range(2210,2220)):
        l.out('k2_22a,2 A,Avsättningar,k2_21,view,account.data_account_type_view,,,l10n_se.b')
        l.out('232k2,2.32,Avsättningar för pensioner och liknande förpliktelser enligt lagen (1967:531) om tryggande av pensionsutfästelserr mm,k2_22a,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","232k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(2230,2240)):
        l.out('233k2,2.33,Övriga avsättningar för pensioner och liknande förpliktelser,k2_22a,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","233k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(2220,2300) and not code in range(2230,2240)):  # exkl 223x
        l.out('233ak2,2.33a,Övriga avsättningar,k2_22a,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","233ak2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])
        
        
# Skulder
    if(code in (range(2310,2330))):
        l.out('k2_23,2 S,Skulder,k2_21,view,account.data_account_type_view,,,l10n_se.b')
        l.out('k2_23a,2 LS,Långfristiga skulder (förfaller senare än 12 månader från balansdagen),k2_23,view,account.data_account_type_view,,,l10n_se.b')
        l.out('235k2,2.35,Obligationslån,k2_23a,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","235k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])        
    if(code in (range(2330,2340))):
        l.out('236k2,2.36,checkräkningskredit,k2_23a,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","236k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in (range(2340,2360))):
        l.out('237k2,2.37,Övriga skulder till kreditinstitut,k2_23a,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","237k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in (range(2360,2380))):
        l.out('238k2,2.38,Skulder till koncern- och intresseföretag,k2_23a,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","238k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in (range(2380,2400))):
        l.out('239k2,2.39,Övriga skulder,k2_23a,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","239k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])

    if(code in (range(2410,2420))):
        l.out('k2_24,2 KS,Kortfristiga skulder (förfaller inom 12 månader från balansdagen),k2_23,view,account.data_account_type_view,,,l10n_se.b')
        l.out('241k2,2.41,Övriga skulder till kreditinstitut,k2_24,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","241k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])         
    if(code in (range(2480,2490))):
        l.out('240k2,2.40,Checkräkningskredit,k2_24,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","240k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])         
    if(code in (range(2420,2430))):
        l.out('242k2,2.42,Förskott från kunder,k2_24,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","242k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])         
    if(code in (range(2430,2440))):
        l.out('243k2,2.43,Pågående arbeten för annans räkning,k2_24,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","243k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])         
    if(code in (range(2450,2460))):
        l.out('244k2,2.44,Fakturerad men ej upparbetad intäkt,k2_24,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","244k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])         
    if(code in (range(2440,2450))):
        l.out('245k2,2.45,Leverantörsskulder,k2_24,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","245k2","payable","account.data_account_type_payable","false",bI,l10n_se.b' % (row[0],code,row[1])         
    if(code == 2492):
        l.out('246k2,2.46,Växelskulder,k2_24,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","246k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])         
    if(code in (range(2460,2480)+range(2860,2880))):
        l.out('247k2,2.47,Skulder till koncern- och intresseföretag,k2_24,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","247k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])         
    if(code in (range(2500,2600))):
        l.out('248k2,2.48,Skatteskulder,k2_24,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","248k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])         
    if(code in (range(2490,2500)+range(2600,2900)) and not (code in range(2860,2880) or code == 2492)):
        l.out('249k2,2.49,Övriga skulder,k2_24,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","249k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])         
    if(code in (range(2900,3000))):
        l.out('250k2,2.50,Upplupna kostnader och förutbetalda intäkter,k2_24,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","250k2","other","account.data_account_type_liability","false",,l10n_se.b' % (row[0],code,row[1])         


# RESULTATRÄKNING

        

    if(code in range(3000,3800) and not (code in range(3002,3005))):
        l.out('k2_3,3,Resultaträkning,K2,view,account.data_account_type_view,,,l10n_se.b')
        l.out('31k2,3.1,"Nettoomsättning",k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","31k2","other","account.data_account_type_income","false",bMP1,l10n_se.b' % (row[0],code,row[1])
    if(code == 3002):  # 12 % 
        print 'k2_%s,%d,"%s","31k2","other","account.data_account_type_income","false",bMP2,l10n_se.b' % (row[0],code,row[1])
    if(code == 3003):  # 6 % 
        print 'k2_%s,%d,"%s","31k2","other","account.data_account_type_income","false",bMP3,l10n_se.b' % (row[0],code,row[1])
    if(code == 3004):  # Momsfria intäkter
        print 'k2_%s,%d,"%s","31k2","other","account.data_account_type_income","false",bMF,l10n_se.b' % (row[0],code,row[1])


        
    if(code in range(4900,5000) and not (code in range(4980,4990) or code in range(4960,4970) or code in range(4910,4932))):
        l.out('32k2,3.2,"Förändring av lager av produkter i arbete, färdiga varor och pågående arbete för annans räkning",k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","32k2","other","account.data_account_type_income","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(3800,3900)):
        l.out('33k2,3.3,Aktiverat arbete för egen räkning,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","33k2","other","account.data_account_type_income","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(3900,4000)):
        l.out('34k2,3.4,Övriga rörelseintäkter,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","34k2","other","account.data_account_type_income","false",,l10n_se.b' % (row[0],code,row[1])


    if(code in range(4000,4800)+range(4910,4932)): 
        l.out('35k2,3.5,"Råvaror och förnödenheter",k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","35k2","other","account.data_account_type_expense","false",bI,l10n_se.b' % (row[0],code,row[1])
    if(code in range(4960,4970)+range(4980,4990) and not code in range(4910,4932)): 
        l.out('36k2,3.6,"Handelsvaror",k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","36k2","other","account.data_account_type_expense","false",bI,l10n_se.b' % (row[0],code,row[1])
    if(code in range(5000,7000)): 
        l.out('37k2,3.7,"Övriga externa kostnader",k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","37k2","other","account.data_account_type_expense","false",bI,l10n_se.b' % (row[0],code,row[1])
    if(code in range(7000,7700)): 
        l.out('38k2,3.8,"Personalkostnader",k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","38k2","other","account.data_account_type_expense","false",bI,l10n_se.b' % (row[0],code,row[1])

    if(code in (range(7740,7750)+range(7790,7800))):
        l.out('310k2,3.10,Nedskrivningar av omsättningstillgångar utöver normala nedskrivningar,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","310k2","other","account.data_account_type_expense","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in (range(7700,7900)) and not (code in range(7740,7750)+range(7790,7800))):
        l.out('39k2,3.9,Av- och nedskrivningar av materiella och immateriella anläggningstillgångar,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","39k2","other","account.data_account_type_expense","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in (range(7900,8000))):
        l.out('311k2,3.11,Övriga rörelsekostnader,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","311k2","other","account.data_account_type_expense","false",,l10n_se.b' % (row[0],code,row[1])

    if(code in (range(8070,8080)+range(8170,8190)+range(8270,8290)+range(8370,8390))):
        l.out('316k2,3.16,Nedskrivningar av finansiella anläggningstillgångar och kortfristiga placeringar,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","316k2","other","account.data_account_type_expense","false",,l10n_se.b' % (row[0],code,row[1])

    if(code in range(8000,8100) and not code in range(8070,8080)):
        l.out('312k2,3.12,Resultat från andelar i koncernföretag,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","312k2","other","account.data_account_type_income","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(8100,8200) and not code in range(8170,8190)):
        l.out('313k2,3.13,Resultat från andelar i intresseföretag,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","313k2","other","account.data_account_type_income","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(8200,8300) and not code in range(8270,8290)):
        l.out('314k2,3.14,Resultat från övriga anläggningstillgångar,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","314k2","other","account.data_account_type_income","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in range(8300,8400) and not code in range(8370,8390)):
        l.out('315k2,3.15,Övriga ränteintäkter och liknande resultatposter,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","315k2","other","account.data_account_type_income","false",,l10n_se.b' % (row[0],code,row[1])

    if(code in (range(8400,8500))):
        l.out('317k2,3.17,Räntekostnader och liknande resultatposter,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","317k2","other","account.data_account_type_expense","false",,l10n_se.b' % (row[0],code,row[1])

    if(code in range(8710,8720)):
        l.out('318k2,3.18,Extraordinära inktäkter,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","318k2","other","account.data_account_type_income","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in (range(8750,8760))):
        l.out('319k2,3.19,Extraordinära kostnader,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","319k2","other","account.data_account_type_expense","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in (range(8830,8840))):
        l.out('320k2,3.20,Lämnade koncernbidrag,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","320k2","other","account.data_account_type_expense","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in (range(8820,8830))):
        l.out('321k2,3.21,Mottagna koncernbidrag,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","321k2","other","account.data_account_type_income","false",,l10n_se.b' % (row[0],code,row[1])

    if((code == 8810) or (code == 8819)):
        l.out('322k2,3.22,Återföring av periodiceringsfond,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","322k2","other","account.data_account_type_asset","false",,l10n_se.b' % (row[0],code,row[1])
    if(code == 8811):
        l.out('323k2,3.23,Avsättning till periodiceringsfond,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","323k2","other","account.data_account_type_asset","false",,l10n_se.b' % (row[0],code,row[1])

    if(code in (range(8850,8860))):
        l.out('324k2,3.24,Förändring av överavskrivning,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","324k2","other","account.data_account_type_expense","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in (range(8860,8900))):
        l.out('325k2,3.25,Övriga bokslutsdispositioner,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%s,%d,"%s","325k2","other","account.data_account_type_expense","false",,l10n_se.b' % (row[0],code,row[1])
        
        
    if(code in (range(8990,9000))):
        l.out('328k2,3.28,Årets resultat. vinst,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%sv,%d,"%s","328k2","other","account.data_account_type_expense","false",,l10n_se.b' % (row[0],code,row[1])
    if(code in (range(8990,9000))):
        l.out('329k2,3.29,Årets resultat. förlust,k2_3,view,account.data_account_type_view,,,l10n_se.b')
#        print 'k2_%sf,%d,"%s","329k2","other","account.data_account_type_expense","false",,l10n_se.b' % (row[0],code,row[1])

    if(code in (range(8900,8990))):
        l.out('326k2,3.26,Skatt på årets resultat,k2_3,view,account.data_account_type_view,,,l10n_se.b')
        print 'k2_%ss,%d,"%s","326k2","other","account.data_account_type_expense","false",,l10n_se.b' % (row[0],code,row[1])
