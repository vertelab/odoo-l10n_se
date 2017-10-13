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
from openerp import models, fields, api, _
import re
from lxml import html

import logging
_logger = logging.getLogger(__name__)

class create_year_end_report(models.TransientModel):
    _name = 'year_end.report'

    data_normal = fields.Binary('BAS Normal')
    data_simplified = fields.Binary('BAS K1 simplified')

    @api.multi
    def send_form(self,):

        l = [
            {'t':'R','f':"Nettoomsättning",'b':"Intäkter som genererats av företagets ordinarie verksamhet, t.ex. varuförsäljning och tjänsteintäkter.",'k':['&', ('code', '>=', '3000'), ('code', '<=', '3799')]},
            {'t':'R','f':"Aktiverat arbete för egen räkning",'b':"Kostnader för eget arbete där resultatet av arbetet tas upp som en tillgång i balansräkningen.",'k':['&', ('code', '>=', '3800'), ('code', '<=', '3899')]},
            {'t':'R','f':"Övriga rörelseintäkter",'b':"Intäkter genererade utanför företagets ordinarie verksamhet, t.ex. valutakursvinster eller realisationsvinster.",'k':['&', ('code', '>=', '3900'), ('code', '<=', '3999')]},
            {'t':'R','f':"Råvaror och förnödenheter",'b':"Årets inköp av råvaror och förnödenheter +/- förändringar av lagerposten ”Råvaror och förnödenheter”. Även kostnader för legoarbeten och underentreprenader.",'k':['|', '|', '|', ('code', '=', '4000'), ('code', '=', '4799'), ('code', '=', '4910'), ('code', '=', '4931')]},
            {'t':'R','f':"Förändring av lager av produkter i arbete, färdiga varor och pågående arbete för annans räkning",'b':"Årets förändring av värdet på produkter i arbete och färdiga egentillverkade varor samt förändring av värde på uppdrag som utförs till fast pris.",'k':[('code', '>=', u'4900'), ('code', '<=', u'4999'), ('code', 'not in', ' [4910,4911,4912,4913,4914,4915,4916,4917,4918,4919,4920,4921,4922,4923,4924,4925,4926,4927,4928,4929,4930,4931,4960,4961,4962,4963,4964,4965,4966,4967,4968,4969,4980,4981,4982,4983,4984,4985,4986,4987,4988,4989]')]},
            {'t':'R','f':"Handelsvaror",'b':"Årets inköp av handelsvaror +/- förändring av lagerposten ”Handelsvaror”.",'k':['|', '|', '|', ('code', '=', '4960'), ('code', '=', '4969'), ('code', '=', '4980'), ('code', '=', '4989')]},
            {'t':'R','f':"Övriga externa kostnader",'b':"Normala kostnader som inte passar någon annan stans, t.ex. lokalhyra, konsultarvoden, telefon, porto, reklam och nedskrivning av kortfristiga fordringar.",'k':['&', ('code', '>=', '5000'), ('code', '<=', '6999')]},
            {'t':'R','f':"Personalkostnader",'b':"",'k':['&', ('code', '>=', '7000'), ('code', '<=', '7699')]},
            {'t':'R','f':"Av- och nedskrivningar av materiella och immateriella anläggningstillgångar",'b':"",'k':[('code', '>=', u'7700'), ('code', '<=', u'7899'), ('code', 'not in', ' [7740,7741,7742,7743,7744,7745,7746,7747,7748,7749,7790,7791,7792,7793,7794,7795,7796,7797,7798,7799]')]},
            {'t':'R','f':"Nedskrivningar av omsättningstillgångar utöver normala nedskrivningar",'b':"Används mycket sällan. Ett exempel är om man gör ovanligt stora nedskrivningar av kundfordringar.",'k':['|', '|', '|', ('code', '=', '7740'), ('code', '=', '7749'), ('code', '=', '7790'), ('code', '=', '7799')]},
            {'t':'R','f':"Övriga rörelsekostnader",'b':"Kostnader som ligger utanför företagets normala verksamhet, t.ex. valutakursförluster och realisationsförlust vid försäljning av icke- finansiella anläggningstillgångar.",'k':['&', ('code', '>=', '7900'), ('code', '<=', '7999')]},
            {'t':'R','f':"Resultat från andelar i koncernföretag",'b':"Nettot av företagets finansiella intäkter och kostnader från koncernföretag med undantag av räntor, koncernbidrag och nedskrivningar, t.ex. erhållna utdelningar, andel i handelsbolags resultat och realisationsresultat.",'k':[('code', '>=', u'8000'), ('code', '<=', u'8099'), ('code', 'not in', ' [8070,8071,8072,8073,8074,8075,8076,8077,8078,8079,8080,8081,8082,8083,8084,8085,8086,8087,8088,8089]')]},
            {'t':'R','f':"Nedskrivningar av finansiella anläggningstillgångar och kortfristiga placeringar",'b':"Nedskrivningar av och återföring av nedskrivningar på finansiella anläggningstillgångar och kortfristiga placeringar",'k':[('code', 'in', ' [8070,8071,8072,8073,8074,8075,8076,8077,8078,8079,8080,8081,8082,8083,8084,8085,8086,8087,8088,8089,8170,8171,8172,8173,8174,8175,8176,8177,8178,8179,8180,8181,8182,8183,8184,8185,8186,8187,8188,8189,8270,8271,8272,8273,8274,8275,8276,8277,8278,8279,8280,8281,8282,8283,8284,8285,8286,8287,8288,8289,8370,8371,8372,8373,8374,8375,8376,8377,8378,8379,8380,8381,8382,8383,8384,8385,8386,8387,8388,8389]')]},
            {'t':'R','f':"Resultat från andelar i intresseföretag och gemensamt styrda företag",'b':"Nettot av företagets finansiella intäkter och kostnader från intresseföretag och gemensamt styrda företag med undantag av räntor och nedskrivningar, t.ex. erhållna utdelningar, andel i handelsbolags resultat och realisationsresultat.",'k':[('code', '>=', u'8100'), ('code', '<=', u'8199'), ('code', 'not in', ' [8170,8171,8172,8173,8174,8175,8176,8177,8178,8179,8180,8181,8182,8183,8184,8185,8186,8187,8188,8189]')]},
            {'t':'R','f':"Resultat från övriga företag som det finns ett ägarintresse i",'b':"Nettot av företagets finansiella intäkter och kostnader från övriga företag som det finns ett ägarintresse i med undantag av räntor och nedskrivningar, t.ex. vissa erhållna vinstutdelningar, andel i handelsbolags resultat och realisationsresultat.",'k':['|', '|', '|', ('code', '=', '8113'), ('code', '=', '8118'), ('code', '=', '8123'), ('code', '=', '8133')]},
            {'t':'R','f':"Resultat från övriga finansiella anläggningstillgångar",'b':"Nettot av intäkter och kostnader från företagets övriga värdepapper och fordringar som är anläggningstillgångar, med undantag av nedskrivningar. T.ex. ränteintäkter (även på värdepapper avseende koncern- och intresseföretag), utdelningar, positiva och negativa valutakursdifferenser och realisationsresultat.",'k':[('code', '>=', u'8200'), ('code', '<=', u'8299'), ('code', 'not in', ' [8270,8271,8272,8273,8274,8275,8276,8277,8278,8279,8280,8281,8282,8283,8284,8285,8286,8287,8288,8289]')]},
            {'t':'R','f':"Övriga ränteintäkter och liknande resultatposter",'b':"Resultat från finansiella omsättningstillgångar med undantag för nedskrivningar. T.ex. ränteintäkter (även dröjsmålsräntor på kundfordringar), utdelningar och positiva valutakursdifferenser.",'k':[('code', '>=', u'8300'), ('code', '<=', u'8399'), ('code', 'not in', ' [8370,8371,8372,8373,8374,8375,8376,8377,8378,8379,8380,8381,8382,8383,8384,8385,8386,8387,8388,8389]')]},
            {'t':'R','f':"Räntekostnader och liknande resultatposter",'b':"Resultat från finansiella skulder, t.ex. räntor på lån, positiva och negativa valutakursdifferenser samt dröjsmåls-räntor på leverantörsskulder.",'k':['&', ('code', '>=', '8400'), ('code', '<=', '8499')]},
            {'t':'R','f':"Extraordinära intäkter",'b':"Används mycket sällan. Får inte användas för räkenskapsår som börjar 2016-01-01 eller senare.",'k':[('code', '=', '8710')]},
            {'t':'R','f':"Extraordinära kostnader",'b':"Används mycket sällan. Får inte användas för räkenskapsår som börjar 2016-01-01 eller senare.",'k':[('code', '=', '8750')]},
            {'t':'R','f':"Förändring av periodiseringsfonder",'b':"",'k':['&', ('code', '>=', '8810'), ('code', '<=', '8819')]},
            {'t':'R','f':"Erhållna koncernbidrag",'b':"",'k':['&', ('code', '>=', '8820'), ('code', '<=', '8829')]},
            {'t':'R','f':"Lämnade koncernbidrag",'b':"",'k':['&', ('code', '>=', '8830'), ('code', '<=', '8839')]},
            {'t':'R','f':"Övriga bokslutsdispositioner",'b':"",'k':['|', '|', '|', ('code', '=', '8840'), ('code', '=', '8849'), ('code', '=', '8860'), ('code', '=', '8899')]},
            {'t':'R','f':"Förändring av överavskrivningar",'b':"",'k':['&', ('code', '>=', '8850'), ('code', '<=', '8859')]},
            {'t':'R','f':"Skatt på årets resultat",'b':"<p>Beräknad skatt på årets resultat.</p><p> Om du inte redan har räknat ut skatten för innevarande år kan du lämna fältet blankt. Skatten räknas ut senare, i sektionen 'Skatt'.</p>",'k':['&', ('code', '>=', '8900'), ('code', '<=', '8979')]},
            {'t':'R','f':"Övriga skatter",'b':"Används sällan.",'k':['&', ('code', '>=', '8980'), ('code', '<=', '8989')]},
            {'t':'B','f':"Koncessioner, patent, licenser, varumärken samt liknande rättigheter",'b':"",'k':[('code', '>=', u'1020'), ('code', '<=', u'1059'), ('code', 'not in', ' [1080,1081,1082,1083,1084,1085,1086,1087,1088,1089]')]},
            {'t':'B','f':"Hyresrätter och liknande rättigheter",'b':"",'k':['&', ('code', '>=', '1060'), ('code', '<=', '1069')]},
            {'t':'B','f':"Goodwill",'b':"",'k':['&', ('code', '>=', '1070'), ('code', '<=', '1079')]},
            {'t':'B','f':"Förskott avseende immateriella anläggningstillgångar",'b':"Förskott i samband med förvärv, t.ex. handpenning och deposition.",'k':[('code', '=', '1088')]},
            {'t':'B','f':"Byggnader och mark",'b':"Förutom byggnader och mark, även maskiner som är avsedda för byggnadens allmänna användning.",'k':[('code', '>=', u'1100'), ('code', '<=', u'1199'), ('code', 'not in', ' [1120,1121,1122,1123,1124,1125,1126,1127,1128,1129,1180,1181,1182,1183,1184,1185,1186,1187,1188,1189]')]},
            {'t':'B','f':"Förbättringsutgifter på annans fastighet",'b':"",'k':['&', ('code', '>=', '1120'), ('code', '<=', '1129')]},
            {'t':'B','f':"Pågående nyanläggningar och förskott avseende materiella anläggningstillgångar",'b':"",'k':['|', '|', '|', ('code', '=', '1180'), ('code', '=', '1189'), ('code', '=', '1280'), ('code', '=', '1289')]},
            {'t':'B','f':"Maskiner och andra tekniska anläggningar",'b':"Maskiner och tekniska anläggningar avsedda för produktionen.",'k':['&', ('code', '>=', '1210'), ('code', '<=', '1219')]},
            {'t':'B','f':"Inventarier, verktyg och installationer",'b':"Om du fyller i detta fält måste du även fylla i motsvarande not i sektionen 'Noter'.",'k':['&', ('code', '>=', '1220'), ('code', '<=', '1279')]},
            {'t':'B','f':"Övriga materiella anläggningstillgångar",'b':"T.ex. djur som klassificerats som anläggningstillgång.",'k':['&', ('code', '>=', '1290'), ('code', '<=', '1299')]},
            {'t':'B','f':"Andelar i koncernföretag",'b':"Aktier och andelar i koncernföretag.",'k':['&', ('code', '>=', '1310'), ('code', '<=', '1319')]},
            {'t':'B','f':"Fordringar hos koncernföretag",'b':"Fordringar på koncernföretag som förfaller till betalning senare än 12 månader från balansdagen.",'k':['&', ('code', '>=', '1320'), ('code', '<=', '1329')]},
            {'t':'B','f':"Andelar i intresseföretag och gemensamt styrda företag",'b':"Aktier och andelar i intresseföretag.",'k':[('code', '>=', u'1330'), ('code', '<=', u'1339'), ('code', 'not in', ' [1336,1337]')]},
            {'t':'B','f':"Ägarintressen i övriga företag",'b':"Aktier och andelar i övriga företag som det redovisningskyldiga företaget har ett ägarintresse i.",'k':['&', ('code', '>=', '1336'), ('code', '<=', '1337')]},
            {'t':'B','f':"Fordringar hos intresseföretag och gemensamt styrda företag",'b':"Fordringar på intresseföretag och gemensamt styrda företag, som förfaller till betalning senare än 12 månader från balansdagen.",'k':[('code', '>=', u'1340'), ('code', '<=', u'1349'), ('code', 'not in', ' [1346,1347]')]},
            {'t':'B','f':"Fordringar hos övriga företag som det finns ett ägarintresse i",'b':"Fordringar på övriga företag som det finns ett ägarintresse i och som ska betalas senare än 12 månader från balansdagen.",'k':['&', ('code', '>=', '1346'), ('code', '<=', '1347')]},
            {'t':'B','f':"Andra långfristiga värdepappersinnehav",'b':"Långsiktigt innehav av värdepapper som inte avser koncern- eller intresseföretag.",'k':['&', ('code', '>=', '1350'), ('code', '<=', '1359')]},
            {'t':'B','f':"Lån till delägare eller närstående",'b':"Fordringar på delägare, och andra som står delägare nära, som förfaller till betalning senare än 12 månader från balansdagen.",'k':['&', ('code', '>=', '1360'), ('code', '<=', '1369')]},
            {'t':'B','f':"Andra långfristiga fordringar",'b':"Fordringar som förfaller till betalning senare än 12 månader från balansdagen.",'k':['&', ('code', '>=', '1380'), ('code', '<=', '1389')]},
            {'t':'B','f':"Råvaror och förnödenheter",'b':"Lager av råvaror eller förnödenheter som har köpts för att bearbetas eller för att vara komponenter i den egna tillverkgningen.",'k':['&', ('code', '>=', '1410'), ('code', '<=', '1429')]},
            {'t':'B','f':"Varor under tillverkning",'b':"Lager av varor där tillverkning har påbörjats.",'k':['|', '|', ('code', '=', u'1432'), ('code', '=', u'1449'), ('code', '=', u'1438')]},
            {'t':'B','f':"Färdiga varor och handelsvaror",'b':"Lager av färdiga egentillverkade varor eller varor som har köpts för vidareförsäljning (handelsvaror).",'k':['&', ('code', '>=', '1450'), ('code', '<=', '1469')]},
            {'t':'B','f':"Pågående arbete för annans räkning",'b':"Om du fyller i detta fält måste du även fylla i motsvarande not i sektionen 'Noter'.",'k':['&', ('code', '>=', '1470'), ('code', '<=', '1479')]},
            {'t':'B','f':"Förskott till leverantörer",'b':"Betalningar och obetalda fakturor för varor och tjänster som redovisas som lager men där prestationen ännu inte erhållits.",'k':['&', ('code', '>=', '1480'), ('code', '<=', '1489')]},
            {'t':'B','f':"Övriga lagertillgångar",'b':"Lager av värdepapper (t.ex. lageraktier), lagerfastigheter och djur som klassificerats som omsättningstillgång.",'k':['&', ('code', '>=', '1490'), ('code', '<=', '1499')]},
            {'t':'B','f':"Kundfordringar",'b':"",'k':['|', '|', '|', ('code', '=', '1500'), ('code', '=', '1559'), ('code', '=', '1580'), ('code', '=', '1589')]},
            {'t':'B','f':"Fordringar hos koncernföretag",'b':"Fordringar på koncernföretag, inklusive kundfordringar.",'k':['|', '|', '|', ('code', '=', '1560'), ('code', '=', '1569'), ('code', '=', '1660'), ('code', '=', '1669')]},
            {'t':'B','f':"Fordringar hos intresseföretag och gemensamt styrda företag",'b':"Fordringar på intresseföretag och gemensamt styrda företag, inklusive kundfordringar.",'k':[('code', '>=', u'1570'), ('code', '<=', u'1579'), ('code', 'not in', ' [1670,1671,1672,1673,1674,1675,1676,1677,1678,1679]')]},
            {'t':'B','f':"Fordringar hos övriga företag som det finns ett ägarintresse i",'b':"Fordringar på övriga företag som det finns ett ägarintresse i, inklusive kundfordringar.",'k':['|', ('code', '=', '1573'), ('code', '=', '1673')]},
            {'t':'B','f':"Övriga fordringar",'b':"T.ex. aktuella skattefordringar.",'k':[('code', 'in', '[1590,1591,1592,1593,1594,1595,1596,1597,1598,1599,1600,1601,1602,1603,1604,1605,1606,1607,1608,1609,1610,1611,1612,1613,1614,1615,1616,1617,1618,1619,1620,1621,1622,1623,1624,1625,1626,1627,1628,1629,1630]')]},
            {'t':'B','f':"Upparbetad men ej fakturerad intäkt",'b':"Upparbetade men ej fakturerade intäkter från uppdrag på löpande räkning eller till fast pris enligt huvudregeln.",'k':['&', ('code', '>=', '1620'), ('code', '<=', '1629')]},
            {'t':'B','f':"Tecknat men ej inbetalat kapital",'b':"Fordringar på aktieägare före tecknat men ej inbetalt kapital. Används vid nyemission.",'k':['&', ('code', '>=', '1690'), ('code', '<=', '1699')]},
            {'t':'B','f':"Förutbetalda kostnader och upplupna intäkter",'b':"Förutbetalda kostnader (t.ex. förutbetalda hyror eller försäkringspremier) och upplupna intäkter (varor eller tjänster som är levererade men där kunden ännu inte betalat).",'k':['&', ('code', '>=', '1700'), ('code', '<=', '1799')]},
            {'t':'B','f':"Övriga kortfristiga placeringar",'b':"Innehav av värdepapper eller andra placeringar som inte är anläggningstillgångar och som inte redovisas i någon annan post under Omsättningstillgångar och som ni planerar att avyttra inom 12 månader från bokföringsårets slut.",'k':[('code', '>=', u'1800'), ('code', '<=', u'1899'), ('code', 'not in', ' [1860,1861,1862,1863,1864,1865,1866,1867,1868,1869]')]},
            {'t':'B','f':"Andelar i koncernföretag",'b':"Här registrerar ni de andelar i koncernföretag som ni planerar att avyttra inom 12 månader från bokföringsårets slut.",'k':['&', ('code', '>=', '1860'), ('code', '<=', '1869')]},
            {'t':'B','f':"Kassa och bank",'b':"",'k':['&', ('code', '>=', '1900'), ('code', '<=', '1989')]},
            {'t':'B','f':"Redovisningsmedel",'b':"",'k':['&', ('code', '>=', '1990'), ('code', '<=', '1999')]},
            {'t':'B','f':"Aktiekapital",'b':"",'k':['|', '|', ('code', '=', '2081'), ('code', '=', '2083'), ('code', '=', '2084')]},
            {'t':'B','f':"Ej registrerat aktiekapital",'b':"Beslutad ökning av aktiekapitalet genom fond- eller nyemission.",'k':[('code', '=', '2082')]},
            {'t':'B','f':"Uppskrivningsfond",'b':"",'k':[('code', '=', '2085')]},
            {'t':'B','f':"Reservfond",'b':"",'k':[('code', '=', '2086')]},
            {'t':'B','f':"Övrigt bundet kapital",'b':"",'k':['&', ('code', '>=', '2087'), ('code', '<=', '2089')]},
            {'t':'B','f':"Balanserat resultat",'b':"Summan av tidigare års vinster och förluster. Registrera balanserat resultat med minustecken om det balanserade resultatet är en balanserad förlust. Är det en balanserad vinst ska du inte använda minustecken.",'k':['|', '|', ('code', '=', '2090'), ('code', '=', '2091'), ('code', '=', '2098')]},
            {'t':'B','f':"Övrigt fritt eget kapital",'b':"",'k':['|', '|', ('code', '=', '2092'), ('code', '=', '2094'), ('code', '=', '2096')]},
            {'t':'B','f':"Aktieägartillskott",'b':"Genom ett aktieägartillskott kan en eller flera aktieägare skjuta till kapital till bolaget. Beloppet förs automatiskt över till resultatdispositionen.",'k':[('code', '=', '2093')]},
            {'t':'B','f':"Överkursfond",'b':"",'k':[('code', '=', '2097')]},
            {'t':'B','f':"Periodiseringsfonder",'b':"Man kan avsätta upp till 25% av resultat efter finansiella poster till periodiseringsfonden. Det är ett sätt att skjuta upp bolagsskatten i upp till fem år. Avsättningen måste återföras till beskattning senast på det sjätte året efter det att avsättningen gjordes.",'k':['&', ('code', '>=', '2110'), ('code', '<=', '2139')]},
            {'t':'B','f':"Ackumulerade överavskrivningar",'b':"",'k':['&', ('code', '>=', '2150'), ('code', '<=', '2159')]},
            {'t':'B','f':"Övriga obeskattade reserver",'b':"",'k':['&', ('code', '>=', '2160'), ('code', '<=', '2199')]},
            {'t':'B','f':"Avsättningar för pensioner och liknande förpliktelser enligt lagen (1967:531) om tryggande av pensionsutfästelse m.m.",'b':"Åtaganden för pensioner enligt tryggandelagen.",'k':['&', ('code', '>=', '2210'), ('code', '<=', '2219')]},
            {'t':'B','f':"Övriga avsättningar",'b':"Andra avsättningar än för pensioner, t.ex. garantiåtaganden.",'k':['|', '|', '|', ('code', '=', '2220'), ('code', '=', '2229'), ('code', '=', '2250'), ('code', '=', '2299')]},
            {'t':'B','f':"Övriga avsättningar för pensioner och liknande förpliktelser",'b':"Övriga pensionsåtaganden till nuvarande och tidigare anställda.",'k':['&', ('code', '>=', '2230'), ('code', '<=', '2239')]},
            {'t':'B','f':"Obligationslån",'b':"",'k':['&', ('code', '>=', '2310'), ('code', '<=', '2329')]},
            {'t':'B','f':"Checkräkningskredit",'b':"",'k':['&', ('code', '>=', '2330'), ('code', '<=', '2339')]},
            {'t':'B','f':"Övriga skulder till kreditinstitut",'b':"",'k':['&', ('code', '>=', '2340'), ('code', '<=', '2359')]},
            {'t':'B','f':"Skulder till koncernföretag",'b':"",'k':['&', ('code', '>=', '2360'), ('code', '<=', '2369')]},
            {'t':'B','f':"Skulder till intresseföretag och gemensamt styrda företag",'b':"",'k':['|', '|', ('code', '=', u'2370'), ('code', '=', u'2379'), ('code', '=', u'2373')]},
            {'t':'B','f':"Skulder till övriga företag som det finns ett ägarintresse i",'b':"",'k':[('code', '=', '2373')]},
            {'t':'B','f':"Övriga skulder",'b':"",'k':['&', ('code', '>=', '2390'), ('code', '<=', '2399')]},
            {'t':'B','f':"Övriga skulder till kreditinstitut",'b':"",'k':['&', ('code', '>=', '2410'), ('code', '<=', '2419')]},
            {'t':'B','f':"Förskott från kunder",'b':"",'k':['&', ('code', '>=', '2420'), ('code', '<=', '2429')]},
            {'t':'B','f':"Pågående arbete för annans räkning",'b':"Om du fyller i detta fält måste du även fylla i motsvarande not i sektionen 'Noter'.",'k':['&', ('code', '>=', '2430'), ('code', '<=', '2439')]},
            {'t':'B','f':"Leverantörsskulder",'b':"",'k':['&', ('code', '>=', '2440'), ('code', '<=', '2449')]},
            {'t':'B','f':"Fakturerad men ej upparbetad intäkt",'b':"",'k':['&', ('code', '>=', '2450'), ('code', '<=', '2459')]},
            {'t':'B','f':"Skulder till koncernföretag",'b':"",'k':['|', '|', '|', ('code', '=', '2460'), ('code', '=', '2469'), ('code', '=', '2860'), ('code', '=', '2869')]},
            {'t':'B','f':"Skulder till intresseföretag och gemensamt styrda företag",'b':"",'k':[('code', '>=', u'2470'), ('code', '<=', u'2479'), ('code', 'not in', ' [2870,2871,2872,2873,2874,2875,2876,2877,2878,2879]')]},
            {'t':'B','f':"Skulder till övriga företag som det finns ett ägarintresse i",'b':"",'k':['|', ('code', '=', '2473'), ('code', '=', '2873')]},
            {'t':'B','f':"Checkräkningskredit",'b':"",'k':['&', ('code', '>=', '2480'), ('code', '<=', '2489')]},
            {'t':'B','f':"Övriga skulder",'b':"",'k':[('code', 'in', '[2490,2491,2493,2494,2495,2496,2497,2498,2499,2600,2601,2602,2603,2604,2605,2606,2607,2608,2609,2610,2611,2612,2613,2614,2615,2616,2617,2618,2619,2620,2621,2622,2623,2624,2625,2626,2627,2628,2629,2630,2631,2632,2633,2634,2635,2636,2637,2638,2639,2640,2641,2642,2643,2644,2645,2646,2647,2648,2649,2650,2651,2652,2653,2654,2655,2656,2657,2658,2659,2660,2661,2662,2663,2664,2665,2666,2667,2668,2669,2670,2671,2672,2673,2674,2675,2676,2677,2678,2679,2680,2681,2682,2683,2684,2685,2686,2687,2688,2689,2690,2691,2692,2693,2694,2695,2696,2697,2698,2699,2700,2701,2702,2703,2704,2705,2706,2707,2708,2709,2710,2711,2712,2713,2714,2715,2716,2717,2718,2719,2720,2721,2722,2723,2724,2725,2726,2727,2728,2729,2730,2731,2732,2733,2734,2735,2736,2737,2738,2739,2740,2741,2742,2743,2744,2745,2746,2747,2748,2749,2750,2751,2752,2753,2754,2755,2756,2757,2758,2759,2760,2761,2762,2763,2764,2765,2766,2767,2768,2769,2770,2771,2772,2773,2774,2775,2776,2777,2778,2779,2780,2781,2782,2783,2784,2785,2786,2787,2788,2789,2790,2791,2792,2793,2794,2795,2796,2797,2798,2799,2810,2811,2812,2813,2814,2815,2816,2817,2818,2819,2820,2821,2822,2823,2824,2825,2826,2827,2828,2829,2830,2831,2832,2833,2834,2835,2836,2837,2838,2839,2840,2841,2842,2843,2844,2845,2846,2847,2848,2849,2850,2851,2852,2853,2854,2855,2856,2857,2858,2859,2880,2881,2882,2883,2884,2885,2886,2887,2888,2889,2890,2891,2892,2893,2894,2895,2896,2897,2898,2899]')]},
            {'t':'B','f':"Växelskulder",'b':"",'k':[('code', '=', '2492')]},
            {'t':'B','f':"Skatteskulder",'b':"",'k':['&', ('code', '>=', '2500'), ('code', '<=', '2599')]},
            {'t':'B','f':"Upplupna kostnader och förutbetalda intäkter",'b':"",'k':['&', ('code', '>=', '2900'), ('code', '<=', '2999')]},
        ]

        year_end = self.env['account.financial.report'].create({'name':u'Resultat och balansräkning (bokslut)','type': 'sum','sequence': 0})
        year_end_r = self.env['account.financial.report'].create({'name':u'Resultaträkning','parent_id': year_end.id,'style_overwrite': 1,'type': 'sum','sequence': 10})
        year_end_b = self.env['account.financial.report'].create({'name':u'Balansräkning','parent_id': year_end.id,'style_overwrite': 1,'type': 'sum','sequence': 20})

        for s,line in enumerate(l):
            if line['t'] == 'B':
                r = self.env['account.financial.report'].create({'name':line['f'],'parent_id': year_end_b.id,'style_overwrite': 3,'type': 'accounts','sequence': s})
                r.account_ids = self.env['account.account'].search(line['k'])
            elif line['t'] == 'R':
                r = self.env['account.financial.report'].create({'name':line['f'],'parent_id': year_end_r.id,'style_overwrite': 3,'type': 'accounts','sequence': s})
                r.account_ids = self.env['account.account'].search(line['k'])





from lxml import html
import requests

import re

import logging
_logger = logging.getLogger(__name__)

def domain(konto):
    k = re.compile('(\d{4})')
    kl = re.compile('(\d{4})-(\d{4})')

    dom = []
    sign = ['>=','<=']
    if k.findall(konto):

        for i,k in enumerate(k.findall(konto)):
           dom.append("('code','%s','%s')" % (sign[i % 2],k))

    return dom


page = requests.get('https://www.arsredovisning-online.se/bas_kontoplan')
tree = html.fromstring(page.content)

data = tree.xpath('//h3/text()')

konton = tree.xpath('//h4/text()')
texter = tree.xpath('//ul/li/text()')
rubr = tree.xpath('//ul/li/b/text()')

print "l = ["
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
    print "{'t':'%s','f':\"%s\",'b':\"%s\",'k':\"%s\"}," % (type,falt.strip(),besk,domain(konton[i]))
    t += 1

print "]"
