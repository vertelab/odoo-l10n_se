from openerp import models, fields, api
import logging
import base64
from lxml import etree

_logger = logging.getLogger(__name__)

class account_vat_decoration(models.Model):
    _inherit = 'account.vat.declaration'
    momsdeklaration_template = fields.Many2one(comodel_name='mis.report', string='Mis_Templates')
    eskd_file_mis = fields.Binary(string="eSKD-file_mis",compute='_compute_xml_file')
    # ~ generated_mis_report_int = fields.Integer(compute='_compute_int_id')
    generated_mis_report_int = fields.Integer()
    generated_mis_report_id = fields.Many2one(comodel_name='mis.report.instance', string='mis_report_instance', default = lambda self: self._generate_mis_report(), ondelete='cascade')

    # ~ This needs to calculated without account.financial.report
    @api.onchange('period_start', 'period_stop', 'target_move','accounting_method','accounting_yearend','name')
    def _vat(self):
         vat_momsutg_list_names = ['MomsUtgHog','MomsUtgMedel','MomsUtgLag','MomsInkopUtgHog','MomsInkopUtgMedel','MomsInkopUtgLag','MomsImportUtgHog', 'MomsImportUtgMedel', 'MomsImportUtgLag']
         # ~ formatNumber = lambda n: n if n%1 else int(n)
         for decl in self:
             if decl.period_start and decl.period_stop and decl.generated_mis_report_id:
                decl.name = str(decl.period_start.date_start)[:7] +"->"+ str(decl.period_stop.date_stop)[5:7]+ " moms report"
                decl.generated_mis_report_id.period_ids.write({'manual_date_from':decl.period_start.date_start})
                decl.generated_mis_report_id.period_ids.write({'manual_date_to':decl.period_stop.date_stop})
                vat_momsutg = 0
                matrix = decl.generated_mis_report_id._compute_matrix()
                for row in matrix.iter_rows():
                    vals = [c.val for c in row.iter_cells()]
                    _logger.warning("jakmar name: {} val: {}".format(row.kpi.name,vals[0]))
                    # ~ _logger.info('jakmar name: {} value: {}'.format(row.kpi.name,vals[0]))
                    if row.kpi.name == 'MomsIngAvdr':
                        decl.vat_momsingavdr = vals[0]
                    if row.kpi.name in vat_momsutg_list_names:
                        decl.vat_momsutg  += vals[0]
                decl.vat_momsbetala = decl.vat_momsutg - decl.vat_momsingavdr
                _logger.warning("jakmar vat_momsbetala{}:".format(decl.vat_momsbetala))
                _logger.warning("jakmar vat_momsutg:{}".format(decl.vat_momsutg))
                _logger.warning("jakmar vat_momsingavdr:".format(decl.vat_momsingavdr))

        
    @api.model
    def _generate_mis_report(self):
        report_instance = self.env["mis.report.instance"].create(
            dict(
                name="mis genererad momsdeklaration report",
                report_id = self.env.ref('l10n_se_mis.report_md').id,
                company_id = self.env.ref("base.main_company").id,
                period_ids=[
                    (
                        0,
                        0,
                        dict(
                            name = "p1",
                            mode = "fix",
                            manual_date_from="2020-01-01",
                            manual_date_to="2020-12-31",
                        ),
                    )
                ],
            )
        )
        return report_instance
            
    @api.model
    def create(self,values):
        start_date = self.env['account.period'].browse(values["period_start"]).date_start
        stop_date = self.env['account.period'].browse(values["period_stop"]).date_stop
        record = super(account_vat_decoration, self).create(values)
        record.generated_mis_report_id.period_ids.write({'manual_date_from':start_date})
        record.generated_mis_report_id.period_ids.write({'manual_date_to':stop_date})
        record.name = str(start_date)[:7] +"->"+ str(stop_date)[5:7]+ " moms report"
        record.generated_mis_report_id.name = str(start_date)[:7] +" to "+ str(stop_date)[5:7]+ " mis report"
        return record
        
    # ~ @api.multi
    # ~ def write(self, values):
        # ~ res = super(account_vat_decoration, self).write(values)
        # ~ mis_instance_record = self.env['mis.report.instance'].browse(self.generated_mis_report_id.id)
        # ~ if "period_start" in values:
            # ~ start_date = self.env['account.period'].browse(values["period_start"]).date_start
            # ~ mis_instance_record.period_ids.write({'manual_date_from':start_date})
        # ~ if "period_stop" in values:
            # ~ stop_date = self.env['account.period'].browse(values["period_stop"]).date_stop
            # ~ mis_instance_record.period_ids.write({'manual_date_to':stop_date})
        # ~ return res
    
    def _compute_xml_file(self):
        if type(self.period_start.date_start) == bool or type(self.period_stop.date_stop) == bool:
            return
        self.eskd_file_mis = None
        root = etree.Element('eSKDUpload', Version="6.0")
        orgnr = etree.SubElement(root, 'OrgNr')
        orgnr.text = self.env.user.company_id.company_registry or ''
        moms = etree.SubElement(root, 'Moms')
        period = etree.SubElement(moms, 'Period')
        period.text = str(self.period_stop.date_start)[:4] + str(self.period_stop.date_start)[5:7]
        matrix = self.generated_mis_report_id._compute_matrix()
        
        # ~ Lambda is used to fix trailing zeros, like example
        formatNumber = lambda n: n if n%1 else int(n)
        for row in matrix.iter_rows():
            vals = [c.val for c in row.iter_cells()]
            # If the vals[0] is zero it becomes a class 'odoo.addons.mis_builder.models.accounting_none.AccountingNoneType. Otherwise it's a float and should be added to the file
            if  type(vals[0]) == float and vals[0] > 0.0:
                tax = etree.SubElement(moms, row.kpi.name)
                tax.text = str(formatNumber(vals[0]))
        
        momsbetala = etree.SubElement(moms, 'MomsBetala')
        momsbetala.text = str(int(round(self.vat_momsbetala)))
        # ~ momsbetala.text = self.vat_momsbetala
        free_text = etree.SubElement(moms, 'TextUpplysningMoms')
        free_text.text = self.free_text or ''
        xml_byte_string = etree.tostring(root, pretty_print=True, encoding='ISO-8859-1')
        xml = xml_byte_string.decode('ISO-8859-1')
        xml = xml.replace('?>', '?>\n<!DOCTYPE eSKDUpload PUBLIC "-//Skatteverket, Sweden//DTD Skatteverket eSKDUpload-DTD Version 6.0//SV" "https://www.skatteverket.se/download/18.3f4496fd14864cc5ac99cb1/1415022101213/eSKDUpload_6p0.dtd">')
        xml_byte_string = xml.encode('ISO-8859-1')
        self.eskd_file_mis = base64.b64encode(xml_byte_string)
        
        # ~ self.get_account_move_ids()
        
    # ~ @api.multi
    def  show_preview(self):
        self.ensure_one()
        return self.generated_mis_report_id.preview()
    
    # ~ @api.multi
    def get_all_account_move_ids(self, row_kpi_names):
        self.ensure_one()
        move_line_recordset = self.env['account.move.line']
        period_id = self.generated_mis_report_id.period_ids[0].id
        matrix = self.generated_mis_report_id._compute_matrix()
        for row in matrix.iter_rows():
            # ~ Just gather up all account.move.lines if list is empty.
            if(len(row_kpi_names) == 0 or row.kpi.name in row_kpi_names):
                _logger.info('jakmar:{}'.format(row.kpi.name))
                for cell in row.iter_cells():
                        drilldown_arg = cell.drilldown_arg
                        res = self.generated_mis_report_id.drilldown(drilldown_arg)
                        move_line_recordset += self.env['account.move.line'].search(res['domain'])
        return move_line_recordset
        
        return self.get_move_ids_from_line_ids(move_line_recordset)
        

    # ~ @api.multi
    def get_move_ids_from_line_ids(self,move_line_recordset):
        move_recordset = self.env['account.move']
        for line in move_line_recordset:
                move_recordset |= line.move_id
        _logger.info('jakmar ids: {}'.format(move_recordset))
        return move_recordset
    

    # ~ @api.multi
    def show_journal_entries_mis(self):
        move_line_recordset= self.get_all_account_move_ids([])
        move_recordset = self.get_move_ids_from_line_ids(move_line_recordset)
        ctx = {
            'period_start': self.period_start.id,
            'period_stop': self.period_stop.id,
            'accounting_yearend': self.accounting_yearend,
            'accounting_method': self.accounting_method,
            'target_move': self.target_move,
        }
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_journal_line')
        action.update({
            'display_name': 'Verifikat',
            'domain': [('id', 'in', move_recordset.mapped('id'))],
            'context': ctx,
        })
        return action
        
        
    # ~ @api.multi
    def show_momsingavdr_mis(self):
        move_line_recordset= self.get_all_account_move_ids(['MomsIngAvdr'])
        ctx = {
                'period_start': self.period_start.id,
                'period_stop': self.period_stop.id,
                'accounting_yearend': self.accounting_yearend,
                'accounting_method': self.accounting_method,
                'target_move': self.target_move,
            }
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_a')
        action.update({
            'display_name': 'VAT In',
            'domain': [('id', 'in', move_line_recordset.mapped('id'))],
            'context': {},
        })
        return action
        
        
    # ~ @api.multi
    def show_momsutg_mis(self):
        vat_momsutg_list_names = ['MomsUtgHog','MomsUtgMedel','MomsUtgLag','MomsInkopUtgHog','MomsInkopUtgMedel','MomsInkopUtgLag','MomsImportUtgHog', 'MomsImportUtgMedel', 'MomsImportUtgLag']
        move_line_recordset= self.get_all_account_move_ids(vat_momsutg_list_names)
        ctx = {
                'period_start': self.period_start.id,
                'period_stop': self.period_stop.id,
                'accounting_yearend': self.accounting_yearend,
                'accounting_method': self.accounting_method,
                'target_move': self.target_move,
            }
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_a')
        action.update({
            'display_name': 'VAT Out',
            'domain': [('id', 'in', move_line_recordset.mapped('id'))],
            'context': {},
        })
        return action



class mis_report_instance(models.Model):
    _inherit = 'mis.report.instance'
    # ~ Should be one2one. account.vat.declaration should have one unique mis.report.instance. This is to insure that the instance created also gets deleted when the account.vat.declaration does.
    account_vat_declaration_id = fields.One2many(comodel_name='account.vat.declaration', inverse_name ='generated_mis_report_id', string="account vat deckaration id")
    
class account_move(models.Model):
    _inherit = 'account.move'
    # ~ Should be one2one. account.vat.declaration should have one unique mis.report.instance. This is to insure that the instance created also gets deleted when the account.vat.declaration does.
    account_vat_declaration_id = fields.One2many(comodel_name='account.vat.declaration', inverse_name ='generated_mis_report_id', string="account vat deckaration id")





# ~ {'name': '#06: Momspliktiga uttag - p1',
 # ~ 'domain': ['&', '&', ('tax_line_id.name', '=', 'MU1'), ('account_id', 'in', (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 522, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532, 533, 534, 535, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559, 560, 561, 562, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 580, 581, 582, 583, 584, 585, 586, 587, 588, 589, 590, 591, 592, 593, 594, 595, 596, 597, 598, 599, 600, 601, 602, 603, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616, 617, 618, 619, 620, 621, 622, 623, 624, 625, 626, 627, 628, 629, 630, 631, 632, 633, 634, 635, 636, 637, 638, 639, 640, 641, 642, 643, 644, 645, 646, 647, 648, 649, 650, 651, 652, 653, 654, 655, 656, 657, 658, 659, 660, 661, 662, 663, 664, 665, 666, 667, 668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679, 680, 681, 682, 683, 684, 685, 686, 687, 688, 689, 690, 691, 692, 693, 694, 695, 696, 697, 698, 699, 700, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712, 713, 714, 715, 716, 717, 718, 719, 720, 721, 722, 723, 724, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 735, 736, 737, 738, 739, 740, 741, 742, 743, 744, 745, 746, 747, 748, 749, 750, 751, 752, 753, 754, 755, 756, 757, 758, 759, 760, 761, 762, 763, 764, 765, 766, 767, 768, 769, 770, 771, 772, 773, 774, 775, 776, 777, 778, 779, 780, 781, 782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794, 795, 796, 797, 798, 799, 800, 801, 802, 803, 804, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 815, 816, 817, 818, 819, 820, 821, 822, 823, 824, 825, 826, 827, 828, 829, 830, 831, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 842, 843, 844, 845, 846, 847, 848, 849, 850, 851, 852, 853, 854, 855, 856, 857, 858, 859, 860, 861, 862, 863, 864, 865, 866, 867, 868, 869, 870, 871, 872, 873, 874, 875, 876, 877, 878, 879, 880, 881, 882, 883, 884, 885, 886, 887, 888, 889, 890, 891, 892, 893, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 907, 908, 909, 910, 911, 912, 913, 914, 915, 916, 917, 918, 919, 920, 921, 922, 923, 924, 925, 926, 927, 928, 929, 930, 931, 932, 933, 934, 935, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 950, 951, 952, 953, 954, 955, 956, 957, 958, 959, 960, 961, 962, 963, 964, 965, 966, 967, 968, 969, 970, 971, 972, 973, 974, 975, 976, 977, 978, 979, 980, 981, 982, 983, 984, 985, 986, 987, 988, 989, 990, 991, 992, 993, 994, 995, 996, 997, 998, 999, 1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010, 1011, 1012, 1013, 1014, 1015, 1016, 1017, 1018, 1019, 1020, 1021, 1022, 1023, 1024, 1025, 1026, 1027, 1028, 1029, 1030, 1031, 1032, 1033, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1041, 1042, 1043, 1044, 1045, 1046, 1047, 1048, 1049, 1050, 1051, 1052, 1053, 1054)), ('credit', '<>', 0.0), '&', ('date', '>=', datetime.date(2021, 1, 1)), ('date', '<=', datetime.date(2021, 12, 31)), ('move_id.state', '=', 'posted')], 
 # ~ 'type': 'ir.actions.act_window', 'res_model': 'account.move.line', 'views': [[False, 'list'], [False, 'form']], 'view_type': 'list', 'view_mode': 'list', 'target': 'current', 'context': {'active_test': False}} 


# ~ {'row': <odoo.addons.mis_builder.models.kpimatrix.KpiMatrixRow object at 0x7fc7e9df4208>, 
# ~ 'subcol': <odoo.addons.mis_builder.models.kpimatrix.KpiMatrixSubCol object at 0x7fc7e8030f60>, 
# ~ 'val': 330000.0, 
# ~ 'val_rendered': '330 000', 
# ~ 'val_comment': 'ForsMomsEjAnnan = bal[3000, 3001, 3002, 3003, 3510, 3511, 3518, 3520, 3540, 3550, 3560, 3561, 3562, 3563, 3570, 3590, 3600, 3610, 3611, 3612, 3613, 3619, 3620, 3730, 3731, 3732, 3740]* -1', 
# ~ 'style_props': {},
 # ~ 'drilldown_arg': {'expr': 'bal[3000, 3001, 3002, 3003, 3510, 3511, 3518, 3520, 3540, 3550, 3560, 3561, 3562, 3563, 3570, 3590, 3600, 3610, 3611, 3612, 3613, 3619, 3620, 3730, 3731, 3732, 3740]* -1', 'period_id': 1, 'kpi_id': 138}
# ~ , 'val_type': 'num'} 


# ~ row dict: {'_matrix': <odoo.addons.mis_builder.models.kpimatrix.KpiMatrix object at 0x7f2dab325908>, 'kpi': mis.report.kpi(138,), 'account_id': None, 'description': '', 'parent_row': None, 'style_props': {}}

# ~ kpi type: <class 'odoo.api.mis.report.kpi'> 
# ~ 2021-07-09 08:58:17,136 29823 INFO l10n_se_mis odoo.addons.l10n_se_tax_report.models.mis_report_generator: jakmar: kpi dict: 
# ~ {'env': <odoo.api.Environment object at 0x7f13c7ae1b70>,
# ~ '_ids': (138,), '_prefetch': defaultdict(<class 'set'>, 
# ~ {'account.vat.declaration': {1}, 'account.period': {2, 13}, 'account.fiscalyear': {1}, 
# ~ 'res.users': {1, 2}, 'res.company': {1}, 'account.move': set(), 'mail.followers': 
# ~ {177}, 'mail.message': {267, 268, 269}, 'mis.report.instance': {1}, '
# ~ mis.report': {3}, 'res.currency': {18}, 'ir.model': {211}, 
# ~ 'ir.model.fields': {3456, 3457, 3458, 3459, 3460, 3461, 3462, 3463, 3464, 3465, 3466, 3467, 3468, 3469, 3470, 3471, 3472, 3473, 3474, 3475, 3476, 3477, 3478, 3479, 3480, 3481, 3482, 3483, 3484, 3485, 3486, 3487, 3488, 3489, 3490, 3491, 3492, 3493, 3494, 3495, 3496, 3497, 3498, 3499, 3500, 3501, 5705, 5706, 5707, 5592, 3450, 3451, 3452, 3453, 3454, 3455}, 
# ~ 'res.partner': {1}, 
# ~ 'account.chart.template': {1}, 
# ~ 'ir.ui.view': {190}, 
# ~ 'account.tax': {1, 44}, 
# ~ 'resource.calendar': {1}, 
# ~ 'account.journal': {4, 5}, 
# ~ 'account.account': {1}, 
# ~ 'report.paperformat': {1}, 
# ~ 'mis.report.kpi': {138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165},
# ~ 'mis.report.subreport': set(),
# ~ 'mis.report.kpi.expression': {128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127}, 
# ~ 'mis.report.style': set(), 'mis.report.instance.period': {1}, 'account.analytic.account': set(), 'account.analytic.group': set(), 'account.analytic.tag': set(), 'mis.report.subkpi': set(), 'mis.report.query': set()})} 

# ~ _logger.info('jakmar: row type: {}'.format(type(row)))
# ~ _logger.info('jakmar: row id: {}'.format(row.kpi.id))
# ~ _logger.info('jakmar: row expression: {}'.format(row.kpi.expression))
# ~ _logger.info('jakmar: c type: {}'.format(type(row.iter_cells())))
# ~ for a in row.iter_cells():
# ~ _logger.info('jakmar row itercell{}'.format(a))
# ~ _logger.info('jakmar row dict {}'.format(a.__dict__))
# ~ return
# ~ _logger.info('jakmar: kpi type: {}'.format(type(row.kpi)))
# ~ _logger.info('jakmar: kpi dict: {}'.format(row.kpi.__dict__))
# ~ return
# ~ _logger.warning('jakmar: row.kpi dict: {}'.format(dir(row.kpi)))
# ~ _logger.warning('jakmar: row.kpi dict: {}'.format(row.__dict__))
# ~ _logger.warning('jakmar: row.dict: {}'.format(dir(row)))
# ~ _logger.warning('jakmar: kpi id: {}'.format(row.kpi.kpi_expression_id))

