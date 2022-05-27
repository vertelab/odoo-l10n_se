from openerp import models, fields, api
import logging
import base64
from lxml import etree

_logger = logging.getLogger(__name__)

class account_vat_declaration(models.Model):
    _inherit = 'account.vat.declaration'
    eskd_file_mis = fields.Binary(string="eSKD-file",readonly=True)
    # ~ generated_mis_report_id = fields.Many2one(comodel_name='mis.report.instance', string='mis_report_instance', default = lambda self: self._generate_mis_report(), ondelete='cascade', readonly = 'true')
    generated_mis_report_id = fields.Many2one(comodel_name='mis.report.instance', string='mis_report_instance', ondelete='cascade', readonly = 'true')
    find_moves_by_period = fields.Boolean(
    default=False,string="Find Move Based On Period",
    help="A little confusing but vouchers/invoices has dates and which period they belong to. By default the mis report finds moves based on date. If this is checked then we find them based on period"
    )

    @api.depends('name')
    def _change_mis_report_name(self):
        for dec in self:
            dec.generated_mis_report_id.name = dec.name
    
    @api.depends('period_start', 'period_stop', 'target_move','name','find_moves_by_period','accounting_method','accounting_yearend')
    def _vat(self):
         _logger.warning(self.accounting_yearend)
         _logger.warning(self.accounting_method)
         for decl in self:
             decl.vat_momsutg = 0
             decl.vat_momsingavdr = 0
             decl.vat_momsbetala  = 0
             if decl.period_start and decl.period_stop and decl.generated_mis_report_id:
                decl.generated_mis_report_id.write({'find_moves_by_period': decl.find_moves_by_period})
                decl.generated_mis_report_id.period_ids.write({'manual_date_from':decl.period_start.date_start})
                decl.generated_mis_report_id.period_ids.write({'manual_date_to':decl.period_stop.date_stop})
                decl.generated_mis_report_id.write({'target_move':decl.target_move})
                if decl.accounting_yearend:#Om det är bokslutsperiod så är det vara faktura metoden som används.
                        decl.generated_mis_report_id.write({'accounting_method':'invoice'})
                else:
                        decl.generated_mis_report_id.write({'accounting_method':decl.accounting_method})
                
                matrix = decl.generated_mis_report_id._compute_matrix()
                vat_momsutg_list_names = ['MomsUtgHog','MomsUtgMedel','MomsUtgLag','MomsInkopUtgHog','MomsInkopUtgMedel','MomsInkopUtgLag','MomsImportUtgHog', 'MomsImportUtgMedel', 'MomsImportUtgLag']
                for row in matrix.iter_rows():
                    vals = [c.val for c in row.iter_cells()]
                    # ~ _logger.debug("jakmar name: {} val: {}".format(row.kpi.name,vals[0]))
                    # ~ _logger.info('jakmar name: {} value: {}'.format(row.kpi.name,vals[0]))
                    if row.kpi.name == 'MomsIngAvdr':
                        decl.vat_momsingavdr = vals[0]
                    if row.kpi.name in vat_momsutg_list_names:
                        decl.vat_momsutg  += vals[0]
                decl.vat_momsbetala = decl.vat_momsutg - decl.vat_momsingavdr

            
    def calculate(self):
        if self.state not in ['draft']:
            raise Warning("Du kan inte beräkna i denna status, ändra till utkast.")
        if self.state in ['draft']:
            self.state = 'confirmed'

        # ~ mark moves used to build the mis report, i should probebly save the moves on the report somewhere at some. Not a problem atm.
        move_line_recordset= self.get_move_line_recordset([])
        move_recordset = self.get_move_recordset_from_line_recordset(move_line_recordset)
        for move in move_recordset:
            if not move.vat_declaration_id :
                move.vat_declaration_id = self.id
            else:
                _logger.warn(_('Move %s is already assigned to %s' % (move.name, move.vat_declaration_id.name) ))
        
        for move in self.move_ids:
            move.full_reconcile_id = move.line_ids.mapped('full_reconcile_id')[0].id if len(move.line_ids.mapped('full_reconcile_id')) > 0 else None
        
        self.create_eskd_xml_file()

        moms_journal = self.env['account.journal'].search([('name','=','Momsjournal'),('type','=','general'),('code','=','MOMS')])
        if not moms_journal:
            raise Warning('Konfigurera din momsdeklaration journal!, den behöver heta Momsjournal, vara av typen general/diverse, ha MOMS som code')
        else:
            # ~ moms_journal = self.env['account.journal'].browse(int(moms_journal_id))
            momsskuld = moms_journal.default_credit_account_id
            momsfordran = moms_journal.default_debit_account_id
            skattekonto = self.env['account.account'].search([('code', '=', '1630')])
            if momsskuld and momsfordran and skattekonto:
                entry = self.env['account.move'].create({
                    'journal_id': moms_journal.id,
                    'period_id': self.period_start.id,
                    'date': fields.Date.today(),
                    'ref': u'Momsdeklaration',
                })
                if entry:
                    move_line_list = []
                    moms_diff = 0.0
                    
                    move_line_dict = {}
                    
                    
                    # ~ Use mis builder to get lines
                    
                    momsIngMovesRecordSet = self.get_move_line_recordset(['MomsIngAvdr']) #~ Get the account.moves.lines,kollar på 2640 konton, ingående moms go though all account.tax
                    for line in momsIngMovesRecordSet:
                        # ~ gather the amount for lines that has the same account
                        if line.account_id.name in move_line_dict: #~ Check if we already added to the dict
                            move_line_dict[line.account_id.name]['credit']+=line.debit
                        else:
                            move_line_dict[line.account_id.name] = {'account_id':line.account_id.id,'credit':line.debit}
                    
                    for account_name in move_line_dict.keys():
                        move_line_list.append((0, 0, {
                            'name': account_name,
                            'account_id': move_line_dict[account_name]['account_id'],
                            'credit': move_line_dict[account_name]['credit'],
                            'debit': 0.0,
                            'move_id': entry.id,
                        }))
                        moms_diff -= move_line_dict[account_name]['credit']
                        
                    move_line_dict = {}
                    
                    momsUtgMovesRecordSet = self.get_move_line_recordset( ['MomsUtgHog','MomsUtgMedel','MomsUtgLag','MomsInkopUtgHog','MomsInkopUtgMedel','MomsInkopUtgLag','MomsImportUtgHog','MomsImportUtgMedel','MomsImportUtgLag'])
                    for line in momsUtgMovesRecordSet: # kollar på 26xx konton, utgående moms
                        # ~ gather the amount for lines that has the same account
                        if line.account_id.name in move_line_dict: #~ Check if we already added to the dict
                            move_line_dict[line.account_id.name]['debit']+=line.credit
                        else:
                            move_line_dict[line.account_id.name] = {'account_id':line.account_id.id,'debit':line.credit}
                    # ~ _logger.warning(f"jakmar {move_line_dict}")
                    
                    for account_name in move_line_dict.keys():
                        move_line_list.append((0, 0, {
                            'name': account_name,
                            'account_id': move_line_dict[account_name]['account_id'],
                            'debit': move_line_dict[account_name]['debit'],
                            'credit': 0.0,
                            'move_id': entry.id,
                        }))
                        moms_diff += move_line_dict[account_name]['debit']
                        
                    if self.vat_momsbetala < 0.0: # momsfordran, moms ska få tillbaka
                        move_line_list.append((0, 0, {
                            'name': momsfordran.name,
                            'account_id': momsfordran.id, # moms_journal.default_debit_account_id
                            'partner_id': '',
                            'debit': abs(self.vat_momsbetala),
                            'credit': 0.0,
                            'move_id': entry.id,
                        }))
                        move_line_list.append((0, 0, {
                            'name': momsfordran.name,
                            'account_id': momsfordran.id,
                            'partner_id': '',
                            'debit': 0.0,
                            'credit': abs(self.vat_momsbetala),
                            'move_id': entry.id,
                        }))
                        move_line_list.append((0, 0, {
                            'name': skattekonto.name,
                            'account_id': skattekonto.id,
                            'partner_id': self.env.ref('l10n_se.res_partner-SKV').id,
                            'debit': abs(self.vat_momsbetala),
                            'credit': 0.0,
                            'move_id': entry.id,
                        }))
                    if self.vat_momsbetala > 0.0: # moms redovisning, moms ska betalas in
                        move_line_list.append((0, 0, {
                            'name': momsskuld.name,
                            'account_id': momsskuld.id, # moms_journal.default_credit_account_id
                            'partner_id': '',
                            'debit': 0.0,
                            'credit': self.vat_momsbetala,
                            'move_id': entry.id,
                        }))
                        move_line_list.append((0, 0, {
                            'name': momsskuld.name,
                            'account_id': momsskuld.id,
                            'partner_id': '',
                            'debit': self.vat_momsbetala,
                            'credit': 0.0,
                            'move_id': entry.id,
                        }))
                        move_line_list.append((0, 0, {
                            'name': skattekonto.name,
                            'account_id': skattekonto.id,
                            'partner_id': self.env.ref('l10n_se.res_partner-SKV').id,
                            'debit': 0.0,
                            'credit': self.vat_momsbetala,
                            'move_id': entry.id,
                        }))
                    # ~ raise Warning('momsdiff %s momsbetala %s' % ( moms_diff, self.vat_momsbetala))
                    # ~ _logger.warning('<<<<< VALUES: moms_diff = %s vat_momsbetala = %s' % (moms_diff, self.vat_momsbetala))
                    if abs(moms_diff) - abs(self.vat_momsbetala) != 0.0:
                        # ~ raise Warning('momsdiff %s momsbetala %s' % ( moms_diff, self.vat_momsbetala))
                        oresavrundning = self.env['account.account'].search([('code', '=', '3740')])
                        oresavrundning_amount = abs(abs(moms_diff) - abs(self.vat_momsbetala))
                        # ~ test of öresavrundning.
                        # ~ _logger.warning('<<<<< VALUES: oresavrundning = %s oresavrundning_amount = %s' % (oresavrundning, oresavrundning_amount))
                        move_line_list.append((0, 0, {
                            'name': oresavrundning.name,
                            'account_id': oresavrundning.id,
                            'partner_id': '',
                            'debit': oresavrundning_amount if moms_diff < self.vat_momsbetala else 0.0,
                            'credit': oresavrundning_amount if moms_diff > self.vat_momsbetala else 0.0,
                            'move_id': entry.id,
                        }))
                    entry.write({
                        'line_ids': move_line_list,
                    })
                    self.write({'move_id': entry.id})
            else:
                raise Warning(_('Kontomoms: %sst, momsskuld: %s, momsfordran: %s, skattekonto: %s') %(len(kontomoms), momsskuld, momsfordran, skattekonto))   
                        
                    
                    
    def do_draft(self):
        for rec in self:
            create_eskd_xml_file = None
            super(account_vat_declaration, rec).do_draft()
            for move in rec.move_ids:
                move.vat_declaration_id = None 


    def do_cancel(self):
        for rec in self:
            super(account_vat_declaration, rec).do_draft()
            create_eskd_xml_file = None
            for move in rec.move_ids:
                move.vat_declaration_id = None
        
        
    @api.model
    def _generate_mis_report(self, start_date, stop_date, target_move_param, name_param,accounting_method_param, find_moves_by_period_param):
        report_instance = self.env["mis.report.instance"].create(
            dict(
                report_id = self.env.ref('l10n_se_mis.report_md').id,
                company_id = self.env.ref("base.main_company").id,
                target_move = target_move_param,
                name = "MIS Report:" + name_param,
                accounting_method = accounting_method_param,
                find_moves_by_period = find_moves_by_period_param,
                period_ids=[
                    (
                        0,
                        0,
                        dict(
                            name = "p1",
                            mode = "fix",
                            manual_date_from = start_date,
                            manual_date_to = stop_date,
                        ),
                    )
                ],
            )
        )
        return report_instance
            
    @api.model
    def create(self,values):
        record = super(account_vat_declaration, self).create(values)
        
        if record.accounting_yearend:
            accounting_method = 'invoice'
        else:
            accounting_method = record.accounting_method
        record.generated_mis_report_id = self._generate_mis_report(
            record.period_start.date_start, 
            record.period_stop.date_stop, 
            record.target_move, record.name, 
            accounting_method, 
            record.find_moves_by_period
        )
        
        return record
        
    def create_eskd_xml_file(self):
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
        
        # ~ Lambda is used to fix trailing zeros
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
        
    # ~ @api.multi
    def  show_mis_report(self):
        self.ensure_one()
        return self.generated_mis_report_id.preview()
    
    # ~ @api.multi
    def get_move_line_recordset(self, row_kpi_names):
        self.ensure_one()
        move_line_recordset = self.env['account.move.line']
        period_id = self.generated_mis_report_id.period_ids[0].id
        matrix = self.generated_mis_report_id._compute_matrix()
        for row in matrix.iter_rows():
            # ~ Just gather up all account.move.lines if list is empty.
            if(len(row_kpi_names) == 0 or row.kpi.name in row_kpi_names):
                for cell in row.iter_cells():
                        drilldown_arg = cell.drilldown_arg
                        res = self.generated_mis_report_id.drilldown(drilldown_arg)
                        move_line_recordset += self.env['account.move.line'].search(res['domain'])
        return move_line_recordset
        
        

    # ~ @api.multi
    def get_move_recordset_from_line_recordset(self,move_line_recordset):
        move_recordset = self.env['account.move']
        for line in move_line_recordset:
                move_recordset |= line.move_id
        return move_recordset
    

    # ~ @api.multi
    def show_journal_entries_mis(self):
        move_line_recordset= self.get_move_line_recordset([])
        move_recordset = self.get_move_recordset_from_line_recordset(move_line_recordset)
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
        move_line_recordset= self.get_move_line_recordset(['MomsIngAvdr'])
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
        move_line_recordset= self.get_move_line_recordset(vat_momsutg_list_names)
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
    account_vat_declaration_id = fields.One2many(comodel_name='account.vat.declaration', inverse_name ='generated_mis_report_id', string="account vat decaration id")





