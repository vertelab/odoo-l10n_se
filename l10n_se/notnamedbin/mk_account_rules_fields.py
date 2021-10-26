#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf8')

ln = [
{
	't': 'R',
	'f': u "Nettoomsättning",
	'b': "Intäkter som genererats av företagets ordinarie verksamhet, t.ex. varuförsäljning och tjänsteintäkter.",
	'k': ['&', ('code', '>=', '3000'), ('code', '<=', '3799')]
},
{
	't': 'R',
	'f': u "Aktiverat arbete för egen räkning",
	'b': "Kostnader för eget arbete där resultatet av arbetet tas upp som en tillgång i balansräkningen.",
	'k': ['&', ('code', '>=', '3800'), ('code', '<=', '3899')]
},
{
	't': 'R',
	'f': u "Övriga rörelseintäkter",
	'b': "Intäkter genererade utanför företagets ordinarie verksamhet, t.ex. valutakursvinster eller realisationsvinster.",
	'k': ['&', ('code', '>=', '3900'), ('code', '<=', '3999')]
},
{
	't': 'R',
	'f': u "Råvaror och förnödenheter",
	'b': "Årets inköp av råvaror och förnödenheter +/- förändringar av lagerposten ”Råvaror och förnödenheter”. Även kostnader för legoarbeten och underentreprenader.",
	'k': [('code', 'in', '[4000,4001,4002,4003,4004,4005,4006,4007,4008,4009,4010,4011,4012,4013,4014,4015,4016,4017,4018,4019,4020,4021,4022,4023,4024,4025,4026,4027,4028,4029,4030,4031,4032,4033,4034,4035,4036,4037,4038,4039,4040,4041,4042,4043,4044,4045,4046,4047,4048,4049,4050,4051,4052,4053,4054,4055,4056,4057,4058,4059,4060,4061,4062,4063,4064,4065,4066,4067,4068,4069,4070,4071,4072,4073,4074,4075,4076,4077,4078,4079,4080,4081,4082,4083,4084,4085,4086,4087,4088,4089,4090,4091,4092,4093,4094,4095,4096,4097,4098,4099,4100,4101,4102,4103,4104,4105,4106,4107,4108,4109,4110,4111,4112,4113,4114,4115,4116,4117,4118,4119,4120,4121,4122,4123,4124,4125,4126,4127,4128,4129,4130,4131,4132,4133,4134,4135,4136,4137,4138,4139,4140,4141,4142,4143,4144,4145,4146,4147,4148,4149,4150,4151,4152,4153,4154,4155,4156,4157,4158,4159,4160,4161,4162,4163,4164,4165,4166,4167,4168,4169,4170,4171,4172,4173,4174,4175,4176,4177,4178,4179,4180,4181,4182,4183,4184,4185,4186,4187,4188,4189,4190,4191,4192,4193,4194,4195,4196,4197,4198,4199,4200,4201,4202,4203,4204,4205,4206,4207,4208,4209,4210,4211,4212,4213,4214,4215,4216,4217,4218,4219,4220,4221,4222,4223,4224,4225,4226,4227,4228,4229,4230,4231,4232,4233,4234,4235,4236,4237,4238,4239,4240,4241,4242,4243,4244,4245,4246,4247,4248,4249,4250,4251,4252,4253,4254,4255,4256,4257,4258,4259,4260,4261,4262,4263,4264,4265,4266,4267,4268,4269,4270,4271,4272,4273,4274,4275,4276,4277,4278,4279,4280,4281,4282,4283,4284,4285,4286,4287,4288,4289,4290,4291,4292,4293,4294,4295,4296,4297,4298,4299,4300,4301,4302,4303,4304,4305,4306,4307,4308,4309,4310,4311,4312,4313,4314,4315,4316,4317,4318,4319,4320,4321,4322,4323,4324,4325,4326,4327,4328,4329,4330,4331,4332,4333,4334,4335,4336,4337,4338,4339,4340,4341,4342,4343,4344,4345,4346,4347,4348,4349,4350,4351,4352,4353,4354,4355,4356,4357,4358,4359,4360,4361,4362,4363,4364,4365,4366,4367,4368,4369,4370,4371,4372,4373,4374,4375,4376,4377,4378,4379,4380,4381,4382,4383,4384,4385,4386,4387,4388,4389,4390,4391,4392,4393,4394,4395,4396,4397,4398,4399,4400,4401,4402,4403,4404,4405,4406,4407,4408,4409,4410,4411,4412,4413,4414,4415,4416,4417,4418,4419,4420,4421,4422,4423,4424,4425,4426,4427,4428,4429,4430,4431,4432,4433,4434,4435,4436,4437,4438,4439,4440,4441,4442,4443,4444,4445,4446,4447,4448,4449,4450,4451,4452,4453,4454,4455,4456,4457,4458,4459,4460,4461,4462,4463,4464,4465,4466,4467,4468,4469,4470,4471,4472,4473,4474,4475,4476,4477,4478,4479,4480,4481,4482,4483,4484,4485,4486,4487,4488,4489,4490,4491,4492,4493,4494,4495,4496,4497,4498,4499,4500,4501,4502,4503,4504,4505,4506,4507,4508,4509,4510,4511,4512,4513,4514,4515,4516,4517,4518,4519,4520,4521,4522,4523,4524,4525,4526,4527,4528,4529,4530,4531,4532,4533,4534,4535,4536,4537,4538,4539,4540,4541,4542,4543,4544,4545,4546,4547,4548,4549,4550,4551,4552,4553,4554,4555,4556,4557,4558,4559,4560,4561,4562,4563,4564,4565,4566,4567,4568,4569,4570,4571,4572,4573,4574,4575,4576,4577,4578,4579,4580,4581,4582,4583,4584,4585,4586,4587,4588,4589,4590,4591,4592,4593,4594,4595,4596,4597,4598,4599,4600,4601,4602,4603,4604,4605,4606,4607,4608,4609,4610,4611,4612,4613,4614,4615,4616,4617,4618,4619,4620,4621,4622,4623,4624,4625,4626,4627,4628,4629,4630,4631,4632,4633,4634,4635,4636,4637,4638,4639,4640,4641,4642,4643,4644,4645,4646,4647,4648,4649,4650,4651,4652,4653,4654,4655,4656,4657,4658,4659,4660,4661,4662,4663,4664,4665,4666,4667,4668,4669,4670,4671,4672,4673,4674,4675,4676,4677,4678,4679,4680,4681,4682,4683,4684,4685,4686,4687,4688,4689,4690,4691,4692,4693,4694,4695,4696,4697,4698,4699,4700,4701,4702,4703,4704,4705,4706,4707,4708,4709,4710,4711,4712,4713,4714,4715,4716,4717,4718,4719,4720,4721,4722,4723,4724,4725,4726,4727,4728,4729,4730,4731,4732,4733,4734,4735,4736,4737,4738,4739,4740,4741,4742,4743,4744,4745,4746,4747,4748,4749,4750,4751,4752,4753,4754,4755,4756,4757,4758,4759,4760,4761,4762,4763,4764,4765,4766,4767,4768,4769,4770,4771,4772,4773,4774,4775,4776,4777,4778,4779,4780,4781,4782,4783,4784,4785,4786,4787,4788,4789,4790,4791,4792,4793,4794,4795,4796,4797,4798,4799,4910,4911,4912,4913,4914,4915,4916,4917,4918,4919,4920,4921,4922,4923,4924,4925,4926,4927,4928,4929,4930,4931]')]
},
{
	't': 'R',
	'f': u "Förändring av lager av produkter i arbete, färdiga varor och pågående arbete för annans räkning",
	'b': "Årets förändring av värdet på produkter i arbete och färdiga egentillverkade varor samt förändring av värde på uppdrag som utförs till fast pris.",
	'k': [('code', '>=', u '4900'), ('code', '<=', u '4999'), ('code', 'not in', ' [4910,4911,4912,4913,4914,4915,4916,4917,4918,4919,4920,4921,4922,4923,4924,4925,4926,4927,4928,4929,4930,4931,4960,4961,4962,4963,4964,4965,4966,4967,4968,4969,4980,4981,4982,4983,4984,4985,4986,4987,4988,4989]')]
},
{
	't': 'R',
	'f': u "Handelsvaror",
	'b': "Årets inköp av handelsvaror +/- förändring av lagerposten ”Handelsvaror”.",
	'k': [('code', 'in', '[4960,4961,4962,4963,4964,4965,4966,4967,4968,4969,4980,4981,4982,4983,4984,4985,4986,4987,4988,4989]')]
},
{
	't': 'R',
	'f': u "Övriga externa kostnader",
	'b': "Normala kostnader som inte passar någon annan stans, t.ex. lokalhyra, konsultarvoden, telefon, porto, reklam och nedskrivning av kortfristiga fordringar.",
	'k': ['&', ('code', '>=', '5000'), ('code', '<=', '6999')]
},
{
	't': 'R',
	'f': u "Personalkostnader",
	'b': "",
	'k': ['&', ('code', '>=', '7000'), ('code', '<=', '7699')]
},
{
	't': 'R',
	'f': u "Av- och nedskrivningar av materiella och immateriella anläggningstillgångar",
	'b': "",
	'k': [('code', '>=', u '7700'), ('code', '<=', u '7899'), ('code', 'not in', ' [7740,7741,7742,7743,7744,7745,7746,7747,7748,7749,7790,7791,7792,7793,7794,7795,7796,7797,7798,7799]')]
},
{
	't': 'R',
	'f': u "Nedskrivningar av omsättningstillgångar utöver normala nedskrivningar",
	'b': u "Används mycket sällan. Ett exempel är om man gör ovanligt stora nedskrivningar av kundfordringar.",
	'k': [('code', 'in', '[7740,7741,7742,7743,7744,7745,7746,7747,7748,7749,7790,7791,7792,7793,7794,7795,7796,7797,7798,7799]')]
},
{
	't': 'R',
	'f': u "Övriga rörelsekostnader",
	'b': "Kostnader som ligger utanför företagets normala verksamhet, t.ex. valutakursförluster och realisationsförlust vid försäljning av icke- finansiella anläggningstillgångar.",
	'k': ['&', ('code', '>=', '7900'), ('code', '<=', '7999')]
},
{
	't': 'R',
	'f': u "Resultat från andelar i koncernföretag",
	'b': "Nettot av företagets finansiella intäkter och kostnader från koncernföretag med undantag av räntor, koncernbidrag och nedskrivningar, t.ex. erhållna utdelningar, andel i handelsbolags resultat och realisationsresultat.",
	'k': [('code', '>=', u '8000'), ('code', '<=', u '8099'), ('code', 'not in', ' [8070,8071,8072,8073,8074,8075,8076,8077,8078,8079,8080,8081,8082,8083,8084,8085,8086,8087,8088,8089]')]
},
{
	't': 'R',
	'f': u "Nedskrivningar av finansiella anläggningstillgångar och kortfristiga placeringar",
	'b': "Nedskrivningar av och återföring av nedskrivningar på finansiella anläggningstillgångar och kortfristiga placeringar",
	'k': [('code', 'in', '[8070,8071,8072,8073,8074,8075,8076,8077,8078,8079,8080,8081,8082,8083,8084,8085,8086,8087,8088,8089,8170,8171,8172,8173,8174,8175,8176,8177,8178,8179,8180,8181,8182,8183,8184,8185,8186,8187,8188,8189,8270,8271,8272,8273,8274,8275,8276,8277,8278,8279,8280,8281,8282,8283,8284,8285,8286,8287,8288,8289,8370,8371,8372,8373,8374,8375,8376,8377,8378,8379,8380,8381,8382,8383,8384,8385,8386,8387,8388,8389]')]
},
{
	't': 'R',
	'f': u "Resultat från andelar i intresseföretag och gemensamt styrda företag",
	'b': "Nettot av företagets finansiella intäkter och kostnader från intresseföretag och gemensamt styrda företag med undantag av räntor och nedskrivningar, t.ex. erhållna utdelningar, andel i handelsbolags resultat och realisationsresultat.",
	'k': [('code', '>=', u '8100'), ('code', '<=', u '8199'), ('code', 'not in', ' [8170,8171,8172,8173,8174,8175,8176,8177,8178,8179,8180,8181,8182,8183,8184,8185,8186,8187,8188,8189]')]
},
{
	't': 'R',
	'f': u "Resultat från övriga företag som det finns ett ägarintresse i",
	'b': "Nettot av företagets finansiella intäkter och kostnader från övriga företag som det finns ett ägarintresse i med undantag av räntor och nedskrivningar, t.ex. vissa erhållna vinstutdelningar, andel i handelsbolags resultat och realisationsresultat.",
	'k': ['|', '|', '|', ('code', '=', '8113'), ('code', '=', '8118'), ('code', '=', '8123'), ('code', '=', '8133')]
},
{
	't': 'R',
	'f': u "Resultat från övriga finansiella anläggningstillgångar",
	'b': "Nettot av intäkter och kostnader från företagets övriga värdepapper och fordringar som är anläggningstillgångar, med undantag av nedskrivningar. T.ex. ränteintäkter (även på värdepapper avseende koncern- och intresseföretag), utdelningar, positiva och negativa valutakursdifferenser och realisationsresultat.",
	'k': [('code', '>=', u '8200'), ('code', '<=', u '8299'), ('code', 'not in', ' [8270,8271,8272,8273,8274,8275,8276,8277,8278,8279,8280,8281,8282,8283,8284,8285,8286,8287,8288,8289]')]
},
{
	't': 'R',
	'f': u "Övriga ränteintäkter och liknande resultatposter",
	'b': u "Resultat från finansiella omsättningstillgångar med undantag för nedskrivningar. T.ex. ränteintäkter (även dröjsmålsräntor på kundfordringar), utdelningar och positiva valutakursdifferenser.",
	'k': [('code', '>=', u '8300'), ('code', '<=', u '8399'), ('code', 'not in', ' [8370,8371,8372,8373,8374,8375,8376,8377,8378,8379,8380,8381,8382,8383,8384,8385,8386,8387,8388,8389]')]
},
{
	't': 'R',
	'f': u "Räntekostnader och liknande resultatposter",
	'b': "Resultat från finansiella skulder, t.ex. räntor på lån, positiva och negativa valutakursdifferenser samt dröjsmåls-räntor på leverantörsskulder.",
	'k': ['&', ('code', '>=', '8400'), ('code', '<=', '8499')]
},
{
	't': 'R',
	'f': u "Extraordinära intäkter",
	'b': "Används mycket sällan. Får inte användas för räkenskapsår som börjar 2016-01-01 eller senare.",
	'k': [('code', '=', '8710')]
},
{
	't': 'R',
	'f': u "Extraordinära kostnader",
	'b': "Används mycket sällan. Får inte användas för räkenskapsår som börjar 2016-01-01 eller senare.",
	'k': [('code', '=', '8750')]
},
{
	't': 'R',
	'f': u "Förändring av periodiseringsfonder",
	'b': "",
	'k': ['&', ('code', '>=', '8810'), ('code', '<=', '8819')]
},
{
	't': 'R',
	'f': u "Erhållna koncernbidrag",
	'b': "",
	'k': ['&', ('code', '>=', '8820'), ('code', '<=', '8829')]
},
{
	't': 'R',
	'f': u "Lämnade koncernbidrag",
	'b': "",
	'k': ['&', ('code', '>=', '8830'), ('code', '<=', '8839')]
},
{
	't': 'R',
	'f': u "Övriga bokslutsdispositioner",
	'b': "",
	'k': [('code', 'in', '[8840,8841,8842,8843,8844,8845,8846,8847,8848,8849,8860,8861,8862,8863,8864,8865,8866,8867,8868,8869,8870,8871,8872,8873,8874,8875,8876,8877,8878,8879,8880,8881,8882,8883,8884,8885,8886,8887,8888,8889,8890,8891,8892,8893,8894,8895,8896,8897,8898,8899]')]
},
{
	't': 'R',
	'f': u "Förändring av överavskrivningar",
	'b': "",
	'k': ['&', ('code', '>=', '8850'), ('code', '<=', '8859')]
},
{
	't': 'R',
	'f': u "Skatt på årets resultat",
	'b': "<p>Beräknad skatt på årets resultat.</p><p> Om du inte redan har räknat ut skatten för innevarande år kan du lämna fältet blankt. Skatten räknas ut senare, i sektionen 'Skatt'.</p>",
	'k': ['&', ('code', '>=', '8900'), ('code', '<=', '8979')]
},
{
	't': 'R',
	'f': u "Övriga skatter",
	'b': "Används sällan.",
	'k': ['&', ('code', '>=', '8980'), ('code', '<=', '8989')]
},
{
	't': 'R',
	'f': u "Resultat",
	'b': "",
	'k': [('code', 'in', '[8990,8991,8992,8993,8994,8995,8996,8997,8998,8999]')]
},
{
	't': 'B',
	'f': u "Koncessioner, patent, licenser, varumärken samt liknande rättigheter",
	'b': "",
	'k': [('code', 'in', '[1080,1081,1082,1083,1084,1085,1086,1087,1089,1000,1001,1002,1003,1004,1005,1006,1007,1008,1009,1010,1011,1012,1013,1014,1015,1016,1017,1018,1019,1020,1021,1022,1023,1024,1025,1026,1027,1028,1029,1030,1031,1032,1033,1034,1035,1036,1037,1038,1039,1040,1041,1042,1043,1044,1045,1046,1047,1048,1049,1050,1051,1052,1053,1054,1055,1056,1057,1058,1059]')]
},
{
	't': 'B',
	'f': u "Hyresrätter och liknande rättigheter",
	'b': "",
	'k': ['&', ('code', '>=', '1060'), ('code', '<=', '1069')]
},
{
	't': 'B',
	'f': u "Goodwill",
	'b': "",
	'k': ['&', ('code', '>=', '1070'), ('code', '<=', '1079')]
},
{
	't': 'B',
	'f': u "Förskott avseende immateriella anläggningstillgångar",
	'b': "Förskott i samband med förvärv, t.ex. handpenning och deposition.",
	'k': [('code', '=', '1088')]
},
{
	't': 'B',
	'f': u "Byggnader och mark",
	'b': "Förutom byggnader och mark, även maskiner som är avsedda för byggnadens allmänna användning.",
	'k': [('code', '>=', u '1100'), ('code', '<=', u '1199'), ('code', 'not in', ' [1120,1121,1122,1123,1124,1125,1126,1127,1128,1129,1180,1181,1182,1183,1184,1185,1186,1187,1188,1189]')]
},
{
	't': 'B',
	'f': u "Förbättringsutgifter på annans fastighet",
	'b': "",
	'k': ['&', ('code', '>=', '1120'), ('code', '<=', '1129')]
},
{
	't': 'B',
	'f': u "Pågående nyanläggningar och förskott avseende materiella anläggningstillgångar",
	'b': "",
	'k': [('code', 'in', '[1180,1181,1182,1183,1184,1185,1186,1187,1188,1189,1280,1281,1282,1283,1284,1285,1286,1287,1288,1289]')]
},
{
	't': 'B',
	'f': u "Maskiner och andra tekniska anläggningar",
	'b': "Maskiner och tekniska anläggningar avsedda för produktionen.",
	'k': ['&', ('code', '>=', '1210'), ('code', '<=', '1219')]
},
{
	't': 'B',
	'f': u "Inventarier, verktyg och installationer",
	'b': "Om du fyller i detta fält måste du även fylla i motsvarande not i sektionen 'Noter'.",
	'k': ['&', ('code', '>=', '1220'), ('code', '<=', '1279')]
},
{
	't': 'B',
	'f': u "Övriga materiella anläggningstillgångar",
	'b': "T.ex. djur som klassificerats som anläggningstillgång.",
	'k': ['&', ('code', '>=', '1290'), ('code', '<=', '1299')]
},
{
	't': 'B',
	'f': u "Andelar i koncernföretag",
	'b': "Aktier och andelar i koncernföretag.",
	'k': ['&', ('code', '>=', '1310'), ('code', '<=', '1319')]
},
{
	't': 'B',
	'f': u "Fordringar hos koncernföretag",
	'b': u "Fordringar på koncernföretag som förfaller till betalning senare än 12 månader från balansdagen.",
	'k': ['&', ('code', '>=', '1320'), ('code', '<=', '1329')]
},
{
	't': 'B',
	'f': u "Andelar i intresseföretag och gemensamt styrda företag",
	'b': "Aktier och andelar i intresseföretag.",
	'k': [('code', '>=', u '1330'), ('code', '<=', u '1339'), ('code', 'not in', ' [1336,1337]')]
},
{
	't': 'B',
	'f': u "Ägarintressen i övriga företag",
	'b': "Aktier och andelar i övriga företag som det redovisningskyldiga företaget har ett ägarintresse i.",
	'k': ['&', ('code', '>=', '1336'), ('code', '<=', '1337')]
},
{
	't': 'B',
	'f': u "Fordringar hos intresseföretag och gemensamt styrda företag",
	'b': u "Fordringar på intresseföretag och gemensamt styrda företag, som förfaller till betalning senare än 12 månader från balansdagen.",
	'k': [('code', '>=', u '1340'), ('code', '<=', u '1349'), ('code', 'not in', ' [1346,1347]')]
},
{
	't': 'B',
	'f': u "Fordringar hos övriga företag som det finns ett ägarintresse i",
	'b': u "Fordringar på övriga företag som det finns ett ägarintresse i och som ska betalas senare än 12 månader från balansdagen.",
	'k': ['&', ('code', '>=', '1346'), ('code', '<=', '1347')]
},
{
	't': 'B',
	'f': u "Andra långfristiga värdepappersinnehav",
	'b': u "Långsiktigt innehav av värdepapper som inte avser koncern- eller intresseföretag.",
	'k': ['&', ('code', '>=', '1350'), ('code', '<=', '1359')]
},
{
	't': 'B',
	'f': u "Lån till delägare eller närstående",
	'b': u "Fordringar på delägare, och andra som står delägare nära, som förfaller till betalning senare än 12 månader från balansdagen.",
	'k': ['&', ('code', '>=', '1360'), ('code', '<=', '1369')]
},
{
	't': 'B',
	'f': u "Uppskjuten skattefordran",
	'b': u "",
	'k': [('code', 'in', '[1370,1371,1372,1373,1374,1375,1376,1377,1378,1379]')]
},
{
	't': 'B',
	'f': u "Andra långfristiga fordringar",
	'b': u "Fordringar som förfaller till betalning senare än 12 månader från balansdagen.",
	'k': ['&', ('code', '>=', '1380'), ('code', '<=', '1389')]
},
{
	't': 'B',
	'f': u "Råvaror och förnödenheter",
	'b': "Lager av råvaror eller förnödenheter som har köpts för att bearbetas eller för att vara komponenter i den egna tillverkgningen.",
	'k': [('code', 'in', '[1410,1411,1412,1413,1414,1415,1416,1417,1418,1419,1420,1421,1422,1423,1424,1425,1426,1427,1428,1429,1430,1431,1438]')]
},
{
	't': 'B',
	'f': u "Varor under tillverkning",
	'b': "Lager av varor där tillverkning har påbörjats.",
	'k': [('code', '>=', u '1432'), ('code', '<=', u '1449'), ('code', 'not in', '[1438]')]
},
{
	't': 'B',
	'f': u "Färdiga varor och handelsvaror",
	'b': "Lager av färdiga egentillverkade varor eller varor som har köpts för vidareförsäljning (handelsvaror).",
	'k': ['&', ('code', '>=', '1450'), ('code', '<=', '1469')]
},
{
	't': 'B',
	'f': u "Pågående arbete för annans räkning",
	'b': "Om du fyller i detta fält måste du även fylla i motsvarande not i sektionen 'Noter'.",
	'k': ['&', ('code', '>=', '1470'), ('code', '<=', '1479')]
},
{
	't': 'B',
	'f': u "Förskott till leverantörer",
	'b': "Betalningar och obetalda fakturor för varor och tjänster som redovisas som lager men där prestationen ännu inte erhållits.",
	'k': ['&', ('code', '>=', '1480'), ('code', '<=', '1489')]
},
{
	't': 'B',
	'f': u "Övriga lagertillgångar",
	'b': "Lager av värdepapper (t.ex. lageraktier), lagerfastigheter och djur som klassificerats som omsättningstillgång.",
	'k': ['&', ('code', '>=', '1490'), ('code', '<=', '1499')]
},
{
	't': 'B',
	'f': u "Kundfordringar",
	'b': "",
	'k': [('code', 'in', '[1500,1501,1502,1503,1504,1505,1506,1507,1508,1509,1510,1511,1512,1513,1514,1515,1516,1517,1518,1519,1520,1521,1522,1523,1524,1525,1526,1527,1528,1529,1530,1531,1532,1533,1534,1535,1536,1537,1538,1539,1540,1541,1542,1543,1544,1545,1546,1547,1548,1549,1550,1551,1552,1553,1554,1555,1556,1557,1558,1559,1580,1581,1582,1583,1584,1585,1586,1587,1588,1589]')]
},
{
	't': 'B',
	'f': u "Fordringar hos koncernföretag",
	'b': u "Fordringar på koncernföretag, inklusive kundfordringar.",
	'k': [('code', 'in', '[1560,1561,1562,1563,1564,1565,1566,1567,1568,1569,1660,1661,1662,1663,1664,1665,1666,1667,1668,1669]')]
},
{
	't': 'B',
	'f': u "Fordringar hos intresseföretag och gemensamt styrda företag",
	'b': u "Fordringar på intresseföretag och gemensamt styrda företag, inklusive kundfordringar.",
	'k': [('code', 'in', u '[1570,1571,1572,1574,1575,1576,1577,1578,1579,1670,1671,1672,1674,1675,1676,1677,1678,1679]')]
},
{
	't': 'B',
	'f': u "Fordringar hos övriga företag som det finns ett ägarintresse i",
	'b': u "Fordringar på övriga företag som det finns ett ägarintresse i, inklusive kundfordringar.",
	'k': ['|', ('code', '=', '1573'), ('code', '=', '1673')]
},
{
	't': 'B',
	'f': u "Övriga fordringar",
	'b': u "T.ex. aktuella skattefordringar.",
	'k': [('code', 'in', '[1590,1591,1592,1593,1594,1595,1596,1597,1598,1599,1600,1601,1602,1603,1604,1605,1606,1607,1608,1609,1610,1611,1612,1613,1614,1615,1616,1617,1618,1619,1630,1631,1632,1633,1634,1635,1636,1637,1638,1639,1640,1641,1642,1643,1644,1645,1646,1647,1648,1649,1650,1651,1652,1653,1654,1655,1656,1657,1658,1659,1680,1681,1682,1683,1684,1685,1686,1687,1688,1689]')]
},
{
	't': 'B',
	'f': u "Upparbetad men ej fakturerad intäkt",
	'b': "Upparbetade men ej fakturerade intäkter från uppdrag på löpande räkning eller till fast pris enligt huvudregeln.",
	'k': ['&', ('code', '>=', '1620'), ('code', '<=', '1629')]
},
{
	't': 'B',
	'f': u "Tecknat men ej inbetalat kapital",
	'b': "Fordringar på aktieägare före tecknat men ej inbetalt kapital. Används vid nyemission.",
	'k': ['&', ('code', '>=', '1690'), ('code', '<=', '1699')]
},
{
	't': 'B',
	'f': u "Förutbetalda kostnader och upplupna intäkter",
	'b': "Förutbetalda kostnader (t.ex. förutbetalda hyror eller försäkringspremier) och upplupna intäkter (varor eller tjänster som är levererade men där kunden ännu inte betalat).",
	'k': ['&', ('code', '>=', '1700'), ('code', '<=', '1799')]
},
{
	't': 'B',
	'f': u "Övriga kortfristiga placeringar",
	'b': u "Innehav av värdepapper eller andra placeringar som inte är anläggningstillgångar och som inte redovisas i någon annan post under Omsättningstillgångar och som ni planerar att avyttra inom 12 månader från bokföringsårets slut.",
	'k': [('code', '>=', u '1800'), ('code', '<=', u '1899'), ('code', 'not in', ' [1860,1861,1862,1863,1864,1865,1866,1867,1868,1869]')]
},
{
	't': 'B',
	'f': u "Andelar i koncernföretag",
	'b': u "Här registrerar ni de andelar i koncernföretag som ni planerar att avyttra inom 12 månader från bokföringsårets slut.",
	'k': ['&', ('code', '>=', '1860'), ('code', '<=', '1869')]
},
{
	't': 'B',
	'f': u "Kassa och bank",
	'b': "",
	'k': ['&', ('code', '>=', '1900'), ('code', '<=', '1989')]
},
{
	't': 'B',
	'f': u "Redovisningsmedel",
	'b': "",
	'k': ['&', ('code', '>=', '1990'), ('code', '<=', '1999')]
},
{
	't': 'B',
	'f': u "Aktiekapital",
	'b': "",
	'k': [('code', 'in', '[2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035,2036,2037,2038,2039,2040,2041,2042,2043,2044,2045,2046,2047,2048,2049,2050,2051,2052,2053,2054,2055,2056,2057,2058,2059,2060,2061,2062,2063,2064,2065,2066,2070,2071,2072,2080,2081,2083,2084]')]
},
{
	't': 'B',
	'f': u "Årets resultat",
	'b': "",
	'k': [('code', 'in', '[2067,2068,2069,2095,2099]')]
},
{
	't': 'B',
	'f': u "Ej registrerat aktiekapital",
	'b': "Beslutad ökning av aktiekapitalet genom fond- eller nyemission.",
	'k': [('code', '=', '2082')]
},
{
	't': 'B',
	'f': u "Uppskrivningsfond",
	'b': "",
	'k': [('code', '=', '2085')]
},
{
	't': 'B',
	'f': u "Reservfond",
	'b': "",
	'k': [('code', '=', '2086')]
},
{
	't': 'B',
	'f': u "Övrigt bundet kapital",
	'b': "",
	'k': ['&', ('code', '>=', '2087'), ('code', '<=', '2089')]
},
{
	't': 'B',
	'f': u "Balanserat resultat",
	'b': "Summan av tidigare års vinster och förluster. Registrera balanserat resultat med minustecken om det balanserade resultatet är en balanserad förlust. Är det en balanserad vinst ska du inte använda minustecken.",
	'k': ['|', '|', ('code', '=', '2090'), ('code', '=', '2091'), ('code', '=', '2098')]
},
{
	't': 'B',
	'f': u "Övrigt fritt eget kapital",
	'b': "",
	'k': ['|', '|', ('code', '=', '2092'), ('code', '=', '2094'), ('code', '=', '2096')]
},
{
	't': 'B',
	'f': u "Aktieägartillskott",
	'b': "Genom ett aktieägartillskott kan en eller flera aktieägare skjuta till kapital till bolaget. Beloppet förs automatiskt över till resultatdispositionen.",
	'k': [('code', '=', '2093')]
},
{
	't': 'B',
	'f': u "Överkursfond",
	'b': "",
	'k': [('code', '=', '2097')]
},
{
	't': 'B',
	'f': u "Periodiseringsfonder",
	'b': "Man kan avsätta upp till 25% av resultat efter finansiella poster till periodiseringsfonden. Det är ett sätt att skjuta upp bolagsskatten i upp till fem år. Avsättningen måste återföras till beskattning senast på det sjätte året efter det att avsättningen gjordes.",
	'k': ['&', ('code', '>=', '2110'), ('code', '<=', '2139')]
},
{
	't': 'B',
	'f': u "Ackumulerade överavskrivningar",
	'b': "",
	'k': ['&', ('code', '>=', '2150'), ('code', '<=', '2159')]
},
{
	't': 'B',
	'f': u "Övriga obeskattade reserver",
	'b': "",
	'k': ['&', ('code', '>=', '2160'), ('code', '<=', '2199')]
},
{
	't': 'B',
	'f': u "Avsättningar för pensioner och liknande förpliktelser enligt lagen (1967:531) om tryggande av pensionsutfästelse m.m.",
	'b': "Åtaganden för pensioner enligt tryggandelagen.",
	'k': ['&', ('code', '>=', '2210'), ('code', '<=', '2219')]
},
{
	't': 'B',
	'f': u "Övriga avsättningar",
	'b': "Andra avsättningar än för pensioner, t.ex. garantiåtaganden.",
	'k': [('code', 'in', '[2220,2221,2222,2223,2224,2225,2226,2227,2228,2229,2240,2250,2251,2252,2253,2254,2255,2256,2257,2258,2259,2260,2261,2262,2263,2264,2265,2266,2267,2268,2269,2270,2271,2272,2273,2274,2275,2276,2277,2278,2279,2280,2281,2282,2283,2284,2285,2286,2287,2288,2289,2290,2291,2292,2293,2294,2295,2296,2297,2298,2299]')]
},
{
	't': 'B',
	'f': u "Övriga avsättningar för pensioner och liknande förpliktelser",
	'b': "Övriga pensionsåtaganden till nuvarande och tidigare anställda.",
	'k': ['&', ('code', '>=', '2230'), ('code', '<=', '2239')]
},
{
	't': 'B',
	'f': u "Obligationslån",
	'b': "",
	'k': ['&', ('code', '>=', '2310'), ('code', '<=', '2329')]
},
{
	't': 'B',
	'f': u "Checkräkningskredit",
	'b': "",
	'k': ['&', ('code', '>=', '2330'), ('code', '<=', '2339')]
},
{
	't': 'B',
	'f': u "Övriga skulder till kreditinstitut",
	'b': "",
	'k': ['&', ('code', '>=', '2340'), ('code', '<=', '2359')]
},
{
	't': 'B',
	'f': u "Skulder till koncernföretag",
	'b': "",
	'k': ['&', ('code', '>=', '2360'), ('code', '<=', '2369')]
},
{
	't': 'B',
	'f': u "Skulder till intresseföretag och gemensamt styrda företag",
	'b': "",
	'k': [('code', 'in', u '[2370,2371,2372,2373,2374,2375,2376,2377,2378,2379]')]
},
{
	't': 'B',
	'f': u "Skulder till övriga företag som det finns ett ägarintresse i",
	'b': "",
	'k': [('code', '=', '2373')]
},
{
	't': 'B',
	'f': u "Övriga skulder",
	'b': "",
	'k': ['&', ('code', '>=', '2390'), ('code', '<=', '2399')]
},
{
	't': 'B',
	'f': u "Övriga skulder till kreditinstitut",
	'b': "",
	'k': ['&', ('code', '>=', '2410'), ('code', '<=', '2419')]
},
{
	't': 'B',
	'f': u "Förskott från kunder",
	'b': "",
	'k': ['&', ('code', '>=', '2420'), ('code', '<=', '2429')]
},
{
	't': 'B',
	'f': u "Pågående arbete för annans räkning",
	'b': "Om du fyller i detta fält måste du även fylla i motsvarande not i sektionen 'Noter'.",
	'k': ['&', ('code', '>=', '2430'), ('code', '<=', '2439')]
},
{
	't': 'B',
	'f': u "Leverantörsskulder",
	'b': "",
	'k': ['&', ('code', '>=', '2440'), ('code', '<=', '2449')]
},
{
	't': 'B',
	'f': u "Fakturerad men ej upparbetad intäkt",
	'b': "",
	'k': ['&', ('code', '>=', '2450'), ('code', '<=', '2459')]
},
{
	't': 'B',
	'f': u "Skulder till koncernföretag",
	'b': "",
	'k': [('code', 'in', '[2460,2461,2462,2463,2464,2465,2466,2467,2468,2469,2860,2861,2862,2863,2864,2865,2866,2867,2868,2869]')]
},
{
	't': 'B',
	'f': u "Skulder till intresseföretag och gemensamt styrda företag",
	'b': "",
	'k': [('code', 'in', u '[2470,2471,2472,2474,2475,2476,2477,2478,2479,2870,2871,2872,2874,2875,2876,2877,2878,2879]')]
},
{
	't': 'B',
	'f': u "Skulder till övriga företag som det finns ett ägarintresse i",
	'b': "",
	'k': ['|', ('code', '=', '2473'), ('code', '=', '2873')]
},
{
	't': 'B',
	'f': u "Checkräkningskredit",
	'b': "",
	'k': ['&', ('code', '>=', '2480'), ('code', '<=', '2489')]
},
{
	't': 'B',
	'f': u "Övriga skulder",
	'b': "",
	'k': [('code', 'in', '[2490,2491,2493,2494,2495,2496,2497,2498,2499,2600,2601,2602,2603,2604,2605,2606,2607,2608,2609,2610,2611,2612,2613,2614,2615,2616,2617,2618,2619,2620,2621,2622,2623,2624,2625,2626,2627,2628,2629,2630,2631,2632,2633,2634,2635,2636,2637,2638,2639,2640,2641,2642,2643,2644,2645,2646,2647,2648,2649,2650,2651,2652,2653,2654,2655,2656,2657,2658,2659,2660,2661,2662,2663,2664,2665,2666,2667,2668,2669,2670,2671,2672,2673,2674,2675,2676,2677,2678,2679,2680,2681,2682,2683,2684,2685,2686,2687,2688,2689,2690,2691,2692,2693,2694,2695,2696,2697,2698,2699,2700,2701,2702,2703,2704,2705,2706,2707,2708,2709,2710,2711,2712,2713,2714,2715,2716,2717,2718,2719,2720,2721,2722,2723,2724,2725,2726,2727,2728,2729,2730,2731,2732,2733,2734,2735,2736,2737,2738,2739,2740,2741,2742,2743,2744,2745,2746,2747,2748,2749,2750,2751,2752,2753,2754,2755,2756,2757,2758,2759,2760,2761,2762,2763,2764,2765,2766,2767,2768,2769,2770,2771,2772,2773,2774,2775,2776,2777,2778,2779,2780,2781,2782,2783,2784,2785,2786,2787,2788,2789,2790,2791,2792,2793,2794,2795,2796,2797,2798,2799,2810,2811,2812,2813,2814,2815,2816,2817,2818,2819,2820,2821,2822,2823,2824,2825,2826,2827,2828,2829,2830,2831,2832,2833,2834,2835,2836,2837,2838,2839,2840,2841,2842,2843,2844,2845,2846,2847,2848,2849,2850,2851,2852,2853,2854,2855,2856,2857,2858,2859,2880,2881,2882,2883,2884,2885,2886,2887,2888,2889,2890,2891,2892,2893,2894,2895,2896,2897,2898,2899]')]
},
{
	't': 'B',
	'f': u "Växelskulder",
	'b': "",
	'k': [('code', '=', '2492')]
},
{
	't': 'B',
	'f': u "Skatteskulder",
	'b': "",
	'k': ['&', ('code', '>=', '2500'), ('code', '<=', '2599')]
},
{
	't': 'B',
	'f': u "Upplupna kostnader och förutbetalda intäkter",
	'b': "",
	'k': ['&', ('code', '>=', '2900'), ('code', '<=', '2999')]
}, ]


def print_utf8(f,d):
    f.write('{')
    for key in d:
        f.write('"%s":%s, ' %(key, ('u"%s"' % d[key]) if type(d[key]) in (unicode, str) else d[key]))
    f.write('},\n')

f = open('../account_rules_fields.py', 'w')
f.write('# -*- coding: utf-8 -*-\n\nfields = [')
for l in ln:
    d = l.get('k')
    ut = ''
    if u'Kundfordringar' in l.get('f') or  'odring' in l.get('f') or u"Fordringar hos koncernföretag" in l['f']:
        ut = 'account.data_account_type_receivable'
    if 'Kassa och bank' in l.get('f'):
        ut = 'account.data_account_type_liquidity'
    if u'Övriga kortfristiga placeringar' in l.get('f') or  u'Färdiga varor och handelsvaror' in l.get('f') or  u'Varor under tillverkning' in l.get('f') or  u'Pågående arbete för annans räkning' in l.get('f') :
        ut = 'account.data_account_type_current_assets'
    if u'Övriga lagertillgångar' in l.get('f') or u'Koncessioner, patent, licenser, varumärken samt liknande rättigheter' in l.get('f') or u'Hyresrätter och liknande rättigheter' in l.get('f') or 'Goodwill' in l.get('f') or u"Andelar i koncernföretag" in l.get('f')  or u'Andelar i intresse' in l['f'] or u'intressen' in l['f'] or u'Andra långfristiga värdepappersinnehav' in l['f'] or u'Obligationslån' in l['f'] or u'Förbättringsutgifter på annans fastighet' in l['f']:
        ut = 'account.data_account_type_non_current_assets'
    if 'Inventarier' in l.get('f') or 'Maskiner' in l.get('f') or 'Byggnader och mark' in l.get('f') or u'Övriga materiella anläggningstillgångar' in l.get('f'):
        ut = 'account.data_account_type_fixed_assets'

    if u'eriodiseringsfonder' in l.get('f')  or u'Övriga obeskattade reserver' in l.get('f'):
        ut = 'l10n_se.untaxed_reserve'

    if  u'Lån till delägare eller närstående' in l.get('f') or  u'Tecknat men ej inbetalat kapital' in l.get('f') or  u'Fordringar hos intresseföretag' in l.get('f') or  u'Fordringar hos övriga företag som det finns ett ägarintresse i' in l.get('f') or  u'Andra långfristiga fordringar' in l.get('f'):
        if u"12 mån" in l.get('b'):
            ut = 'account.data_account_type_non_current_liabilities'
        else:
            ut = 'account.data_account_type_current_liabilities'
    if u'Skatteskulder' in l.get('f') or u'Uppskjuten skattefordran' in l.get('f'):
        ut = 'account.data_account_type_current_liabilities'
    if u'Ackumulerade överavskrivningar' in l.get('f') or u'Avsättningar för pensioner och liknande förpliktelser' in l.get('f') or u'Övriga avsättningar' in l.get('f') or u'Skulder till koncernföretag' in l.get('f') or u'Skulder till övriga företag som det finns ett ägarintresse i' in l.get('f') or u'Skulder till intresseföretag och gemensamt styrda företag' in l.get('f') or u'Övriga skulder' in l.get('f'):
        ut = 'account.data_account_type_non_current_liabilities'

    if u'Leverantörsskulder' in l.get('f') or  u'Checkräkningskredit' in l.get('f') or  u'Växelskulder' in l.get('f') or  u'Upplupna kostnader och förutbetalda intäkter' in l.get('f') or  u'Övriga fordringar' in l.get('f') or  u'Skattefordringar' in l.get('f') or u'Upparbetad men ej fakturerad intäkt' in l.get('f'):
        ut = 'account.data_account_type_payable'

    if u'Förskott' in l['f'] or u'förskott' in l['f'] or u'Förutbetalda' in l['f'] or u'Fakturerad men ej upparbetad intäkt' in l['f']:
        ut = 'account.data_account_type_prepayments'
    if u'Redovisningsmedel' in l['f']:
        ut = 'l10n_se.trustee_assets'

    if u'Skatt på årets resultat' in l['f'] or u'Övriga skatter' in l['f']:
        ut = 'l10n_se.tax'



    if 'Aktiekapital' in l.get('f') or u'Övrigt bundet kapita' in l.get('f') or u'Övrigt bundet kapita' in l.get('f')  or u'Balanserat resultat' in l.get('f') or u'Övrigt fritt eget kapital' in l.get('f') or u'Ej registrerat aktiekapital' in l.get('f') or u'Uppskrivningsfond' in l.get('f')  or u'Reservfond' in l.get('f') or u'Aktieägartillskott' in l.get('f') or u'Överkursfond' in l.get('f') or u'Övriga bokslutsdispositioner' in l.get('f') or u'Resultat' in l.get('f') or u'Årets resultat' in l.get('f'):
        ut = 'account.data_account_type_equity'
    if u'Nettoomsättning' in l.get('f'):
        ut = 'account.data_account_type_revenue'
    if u'Övriga rörelseintäkter' in l.get('f'):
        ut = 'account.data_account_other_income'
    if u'Extraordinära intäkter' in l.get('f') or u'Erhållna koncernbidrag' in l.get('f') or u'Resultat från ' in l.get('f') or u'Övriga ränteintäkter' in l.get('f'):
        ut = 'account.data_account_type_other_income'
    if u'Aktiverat arbete för egen räkning' in l.get('f') or u'Råvaror och förnödenheter' in l.get('f') or u'Handelsvaror' in l.get('f') or u'Förändring av lager av produkter i arbete' in l.get('f') or u'Av- och nedskrivningar' in l.get('f') or u'Nedskrivningar' in l.get('f') or u'Övriga rörelsekostnader' in l.get('f'):
        ut = 'account.data_account_type_direct_costs'
    if u'Övriga externa kostnader' in l.get('f') or u'Personalkostnader' in l.get('f') or u'Räntekostnader' in l.get('f') or u'Lämnade koncernbidrag' in l.get('f') or u'Förändring av överavskrivningar' in l.get('f'):
        ut = 'account.data_account_type_expenses'




    #~ "data_account_type_prepayments"
    #~ "data_unaffected_earnings"
    #~ "data_account_type_depreciation"

    if l.get('k')[0] == '&':
        li = []
        for i in range(int(l.get('k')[1][2]), int(l.get('k')[2][2])+1):
            li.append(str(i))
        l['k'] = ('code', 'in', li)
        print_utf8(f,{'t':l.get('t'),'f':l.get('f').encode('utf-8'),'b':l.get('b').encode('utf-8'),'k':li,'d':d,'ut':ut})
    elif l.get('k')[0] == '|':
        li = []
        for i in l.get('k'):
            if isinstance(i, tuple):
                li.append(i[2])
        l['k'] = ('code', 'in', li)
        print_utf8(f,{'t':l.get('t'),'f':l.get('f'),'b':l.get('b'),'k':li,'d':d,'ut':ut})
    elif isinstance(l.get('k')[-1], tuple) and (l.get('k')[0] != '&' or '|'):
        li = []
        if len(l.get('k')) == 1:
            if l.get('k')[0][1] == '=':
                li.append(l.get('k')[0][2])
            elif l.get('k')[0][1] == 'in':
                for i in l.get('k')[-1][2].replace('[', '').replace(']', '').strip().split(','):
                    li.append(i)
        else:
            lst = []
            if l.get('k')[-1][1] == 'not in':
                for i in l.get('k')[-1][2].replace('[', '').replace(']', '').strip().split(','):
                    lst.append(i)
            for i in range(int(l.get('k')[0][2]), int(l.get('k')[1][2])+1):
                if str(i) not in lst:
                    li.append(str(i))
        print_utf8(f,{'t':l.get('t'),'f':l.get('f'),'b':l.get('b'),'k':li,'d':d,'ut':ut})
    else:
        print('ERROR: ------ %s ------' %l.get('k'))
f.write(']\n')
f.close()
