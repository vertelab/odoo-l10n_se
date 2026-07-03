from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import base64
import requests
from lxml import etree
from datetime import datetime

_logger = logging.getLogger(__name__)

class account_vat_declaration(models.Model):
    _inherit = 'account.vat.declaration'

    eskd_file_mis = fields.Binary(string="eSKD-file",readonly=True)
    generated_mis_report_id = fields.Many2one(
        comodel_name='mis.report.instance', string='mis_report_instance', ondelete='cascade', readonly=True)
    report_id = fields.Many2one(
        'mis.report', 
        string="Report",
        default=lambda self: self.env.company.vat_report_template_id.id
            or self.env.ref('l10n_se_mis.report_md').id
    )
    
    @api.depends('name')
    def _change_mis_report_name(self):
        for dec in self:
            dec.generated_mis_report_id.name = dec.name
    
    @api.depends('target_move','name','accounting_yearend','company_id', 'report_id', 'date_start', 'date_stop')
    def _vat(self):
         for decl in self:
             decl.vat_momsutg = 0
             decl.vat_momsingavdr = 0
             decl.vat_momsbetala  = 0
             if decl.date_start and decl.date_stop and decl.generated_mis_report_id:
                decl.generated_mis_report_id.period_ids.write({'manual_date_from':decl.date_start})
                decl.generated_mis_report_id.period_ids.write({'manual_date_to':decl.date_stop})
                decl.generated_mis_report_id.write({
                    'target_move': decl.target_move,
                    'report_id': decl.report_id.id,
                })
                ##Faktura vs kontant method betyder ifall man tar fakturor som är betalda eller inte.
                ##Det är betalningens datums som ska användas istället.
                ##Behöver återimplementeras på något sätt.
                #if decl.accounting_yearend:#Om det är bokslutsperiod så är det vara faktura metoden som används.
                #        decl.generated_mis_report_id.write({'company_id':decl.company_id})
                #else:
                #        pass
                        #decl.generated_mis_report_id.write({'accounting_method':decl.accounting_method})
                
                matrix = decl.generated_mis_report_id._compute_matrix()
                vat_momsutg_list_names = ['MomsUtgHog','MomsUtgMedel','MomsUtgLag','MomsInkopUtgHog','MomsInkopUtgMedel','MomsInkopUtgLag','MomsImportUtgHog', 'MomsImportUtgMedel', 'MomsImportUtgLag']
                for row in matrix.iter_rows():
                    vals = [c.val for c in row.iter_cells()]
                    if not isinstance(vals[0], (float, int)):
                        continue
                    if row.kpi.name == 'MomsIngAvdr':
                        decl.vat_momsingavdr = abs(int(round(vals[0])))
                    if row.kpi.name in vat_momsutg_list_names:
                        decl.vat_momsutg += abs(int(round(vals[0])))
                decl.vat_momsbetala = decl.vat_momsutg - decl.vat_momsingavdr

    def calculate(self):
        if self.state not in ['draft']:
            raise UserError(_("Du kan inte beräkna i denna status, ändra till utkast."))
        if self.state in ['draft']:
            self.state = 'confirmed'

        if not self.env.company.vat_declaration_frequency:
            raise UserError(_(
                "VAT declaration frequency is not configured. "
                "Set it in Accounting → Configuration → Settings."))
#            self.generated_mis_report_id.active = True

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

        moms_journal = self.env['account.journal'].search([('company_id','=',self.company_id.id),('name','=','Momsjournal'),('type','=','general'),('code','=','MOMS')])
        if not moms_journal:
            raise UserError('Configure your tax declaration journal! It needs to be named Tax Journal, be of the general/miscellaneous type, and have TAX as the code.')
        else:
            # ~ moms_journal = self.env['account.journal'].browse(int(moms_journal_id))
            momsskuld = moms_journal.default_credit_account_id
            momsfordran = moms_journal.default_debit_account_id
            skattekonto = self.env['account.account'].search([('company_ids','in',[self.company_id.id]),('code', '=', '1630')])
            if momsskuld and momsfordran and skattekonto:
                entry = self.env['account.move'].create({
                    'journal_id': moms_journal.id,
                    #'period_id': self.period_start.id,
                    'date': fields.Date.today(),
                    'ref': u'Momsdeklaration',
                })
                if entry:
                    move_line_list = []
                    moms_diff = 0.0
                    rounding_diff = 0.0
                    all_lines_dict = {}

                    # Process Input VAT (MomsIngAvdr) - Reversal as Credits
                    momsIngMovesRecordSet = self.get_move_line_recordset(['MomsIngAvdr'])
                    
                    # Process Output VAT - Reversal as Debits
                    vat_momsutg_list = ['MomsUtgHog','MomsUtgMedel','MomsUtgLag','MomsInkopUtgHog','MomsInkopUtgMedel','MomsInkopUtgLag','MomsImportUtgHog','MomsImportUtgMedel','MomsImportUtgLag']
                    momsUtgMovesRecordSet = self.get_move_line_recordset(vat_momsutg_list)
                    
                    # Deduplicate: tax lines (e.g. TFEU/VFEU/TFFU on 2614/2624/2634)
                    # appear in both MomsIngAvdr and MomsInkopUtg* KPI groups.
                    # Only process them once to avoid double-counting in the journal entry.
                    moms_ing_line_ids = set(momsIngMovesRecordSet.ids)
                    moms_utg_line_ids = set(momsUtgMovesRecordSet.ids)
                    overlap_ids = moms_ing_line_ids & moms_utg_line_ids
                    
                    for line in momsIngMovesRecordSet:
                        if line.id in overlap_ids:
                            continue  # Skip: will be processed in output VAT loop
                        acc_id = line.account_id.id
                        if acc_id not in all_lines_dict:
                            all_lines_dict[acc_id] = {'name': line.account_id.name, 'balance': 0.0}
                        # Input VAT is usually Debit, so balance (credit - debit) will be negative
                        all_lines_dict[acc_id]['balance'] += (line.credit - line.debit)
                    
                    for line in momsUtgMovesRecordSet:
                        acc_id = line.account_id.id
                        if acc_id not in all_lines_dict:
                            all_lines_dict[acc_id] = {'name': line.account_id.name, 'balance': 0.0}
                        # Output VAT is usually Credit, so balance (credit - debit) will be positive
                        all_lines_dict[acc_id]['balance'] += (line.credit - line.debit)

                    # Convert aggregated dictionary to move lines, rounded to integers
                    for acc_id, vals in all_lines_dict.items():
                        balance = vals['balance']
                        if round(balance, 2) == 0: continue
                        rounded = int(round(balance))
                        if rounded == 0: continue
                        move_line_list.append((0, 0, {
                            'name': vals['name'],
                            'account_id': acc_id,
                            'debit': rounded if rounded > 0 else 0.0,
                            'credit': -rounded if rounded < 0 else 0.0,
                            'move_id': entry.id,
                        }))
                        moms_diff += rounded
                        rounding_diff += balance - rounded

                    # Add öresavrundning line if there is a rounding difference
                    rounding_account = self.env['account.account'].search(
                        [('code', '=', '3740')], limit=1)
                    if rounding_account and round(rounding_diff, 2) != 0.0:
                        move_line_list.append((0, 0, {
                            'name': u'Öresavrundning',
                            'account_id': rounding_account.id,
                            'debit': abs(rounding_diff) if rounding_diff < 0.0 else 0.0,
                            'credit': rounding_diff if rounding_diff > 0.0 else 0.0,
                            'move_id': entry.id,
                        }))
                        moms_diff -= rounding_diff

                    # Settlement logic: use moms_diff (net of all reversed tax lines)
                    # as the balancing line against the tax account (1630).
                    if moms_diff != 0.0:
                        move_line_list.append((0, 0, {
                            'name': skattekonto.name,
                            'account_id': skattekonto.id,
                            'partner_id': self.env.ref('l10n_se_tax_report.res_partner-SKV').id,
                            'debit': abs(moms_diff) if moms_diff < 0.0 else 0.0,
                            'credit': moms_diff if moms_diff > 0.0 else 0.0,
                            'move_id': entry.id,
                        }))
                    entry.write({
                        'line_ids': move_line_list,
                    })
                    self.write({'move_id': entry.id})
            else:
                raise UserError(_('You are missing either a credit account, debit account or a tax account, please add these'))   

                    
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
    def _generate_mis_report(self, start_date, stop_date, target_move_param, name_param, accounting_method_param, company_id, report_id=None):
        report_instance = self.env["mis.report.instance"].create(
            dict(
                report_id = report_id or self.env.ref('l10n_se_mis.report_md').id,
                target_move = target_move_param,
                name = "MIS Report:" + name_param,
                company_id = company_id.id,
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
            if not record.company_id.accounting_method:
                raise UserError(_(
                    "Accounting method is not configured for company %s. "
                    "Set it in Accounting → Configuration → Settings.")
                    % record.company_id.name)
            accounting_method = record.company_id.accounting_method
        record.generated_mis_report_id = self._generate_mis_report(
            record.date_start, 
            record.date_stop, 
            record.target_move, 
            record.name, 
            accounting_method, 
            record.company_id,
            report_id=record.report_id.id,
        )
        
        return record
        
    def create_eskd_xml_file(self):
        if type(self.date_start) == bool or type(self.date_stop) == bool:
            return
        self.eskd_file_mis = None
        root = etree.Element('eSKDUpload', Version="6.0")
        orgnr = etree.SubElement(root, 'OrgNr')
        orgnr.text = self.env.user.company_id.company_registry or ''
        moms = etree.SubElement(root, 'Moms')
        period = etree.SubElement(moms, 'Period')
        period.text = str(self.date_start)[:4] + str(self.date_start)[5:7]
        matrix = self.generated_mis_report_id._compute_matrix()
        
        for row in matrix.iter_rows():
            vals = [c.val for c in row.iter_cells()]
            if isinstance(vals[0], (float, int)) and vals[0] > 0:
                tax = etree.SubElement(moms, row.kpi.name)
                tax.text = str(int(round(vals[0])))
        
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
        
    def show_mis_report(self):
        action_context = {'active_id': self.generated_mis_report_id.id, 'active_model': self.generated_mis_report_id._name}
        return self.generated_mis_report_id.with_context(action_context).preview()

    # ~ @api.multi
    def get_move_line_recordset(self, row_kpi_names):
        self.ensure_one()
        move_line_recordset = self.env['account.move.line']
        matrix = self.generated_mis_report_id._compute_matrix()
        for row in matrix.iter_rows():
            # ~ Just gather up all account.move.lines if list is empty.
            if(len(row_kpi_names) == 0 or row.kpi.name in row_kpi_names):
                for cell in row.iter_cells():
                        drilldown_arg = cell.drilldown_arg
                        res = self.generated_mis_report_id.drilldown(drilldown_arg)
                        move_line_recordset += self.env['account.move.line'].search(res['domain'])
        return move_line_recordset
        
        

    def get_move_recordset_from_line_recordset(self,move_line_recordset):
        move_recordset = self.env['account.move']
        for line in move_line_recordset:
                move_recordset |= line.move_id
        return move_recordset
    

    def show_journal_entries_mis(self):
        move_line_recordset= self.get_move_line_recordset([])
        move_recordset = self.get_move_recordset_from_line_recordset(move_line_recordset)

        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_journal_line')
        action.update({
            'display_name': 'Verifikat',
            'domain': [('id', 'in', move_recordset.mapped('id'))],
        })
        return action
        

    def show_momsingavdr_mis(self):
        move_line_recordset= self.get_move_line_recordset(['MomsIngAvdr'])
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_a')
        action.update({
            'display_name': 'VAT In',
            'domain': [('id', 'in', move_line_recordset.mapped('id'))],
        })
        return action
        
        
    def show_momsutg_mis(self):
        vat_momsutg_list_names = ['MomsUtgHog','MomsUtgMedel','MomsUtgLag','MomsInkopUtgHog','MomsInkopUtgMedel','MomsInkopUtgLag','MomsImportUtgHog', 'MomsImportUtgMedel', 'MomsImportUtgLag']
        move_line_recordset= self.get_move_line_recordset(vat_momsutg_list_names)
        
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_a')
        action.update({
            'display_name': 'VAT Out',
            'domain': [('id', 'in', move_line_recordset.mapped('id'))],
        })
        return action

    # --- Skatteverket API: submit VAT declaration ---

    def action_send_to_skv(self):
        """Submit the VAT declaration to Skatteverket via API."""
        self.ensure_one()

        # Ensure eSKD XML is generated
        if not self.eskd_file_mis:
            if self.state not in ['draft', 'confirmed']:
                self.do_draft()
            self.calculate()
        if not self.eskd_file_mis:
            raise UserError(_(
                "Could not generate eSKD XML file. "
                "Please run 'Calculate' first and check MIS report."))

        company = self.company_id or self.env.company
        url = company.skv_moms_api_url
        access_token = self._get_skv_access_token(company)

        xml_bytes = base64.b64decode(self.eskd_file_mis)
        response = self._skv_api_call(url, xml_bytes, access_token=access_token)
        try:
            result = self._handle_skv_response(response, company)
            result['state'] = 'done'
            self.write(result)
        except UserError:
            self.write({
                'skv_api_status': 'error',
                'skv_response': 'HTTP %s: %s' % (response.status_code, response.text[:1000]),
                'skv_submitted_date': fields.Datetime.now(),
            })
            raise

    @api.model
    def _demo_fill_declarations(self):
        """Create demo journal entries that fill all SKV form fields
        for the two demo declarations (May 2026 and June 2026).
        Uses tax codes from NAMEMAPPING to populate the MIS report."""
        _logger.info("Creating demo journal entries for VAT declarations...")

        AccountAccount = self.env['account.account']
        AccountTax = self.env['account.tax']
        AccountJournal = self.env['account.journal']
        AccountMove = self.env['account.move']

        # Find accounts by code
        def find_acc(code):
            return AccountAccount.search([
                ('company_ids', 'in', [self.env.company.id]),
                ('code', '=', code)
            ], limit=1)

        def find_tax(name):
            return AccountTax.search([
                ('company_id', '=', self.env.company.id),
                ('name', '=', name)
            ], limit=1)

        sale_journal = AccountJournal.search([('type', '=', 'sale')], limit=1)
        purchase_journal = AccountJournal.search([('type', '=', 'purchase')], limit=1)
        bank_journal = AccountJournal.search([('type', '=', 'bank')], limit=1)

        if not sale_journal or not purchase_journal:
            _logger.warning("Cannot create demo entries: no sale/purchase journal found")
            return False

        partner = self.env['res.partner'].search([('name', '=', 'Skatteverket API (Test)')], limit=1)
        if not partner:
            partner = self.env.ref('l10n_se_tax_report.partner_eu_germany', raise_if_not_found=False)
        if not partner:
            partner = self.env.ref('l10n_se_tax_report.partner_skv_api', raise_if_not_found=False)
        if not partner:
            partner = self.env['res.partner'].search([('is_company', '=', True)], limit=1)
        if not partner:
            return False

        # Partner for non-EU
        partner_us = self.env.ref('l10n_se_tax_report.partner_non_eu', raise_if_not_found=False) or partner
        partner_eu = self.env.ref('l10n_se_tax_report.partner_eu_france', raise_if_not_found=False) or partner

        moves_to_post = []

        def create_invoice(move_type, date_str, lines, journal=None, partner_id=None):
            jrnl = journal or (sale_journal if move_type == 'out_invoice' else purchase_journal)
            partner = partner_id or (partner_eu if move_type == 'out_invoice' else partner)
            inv_lines = []
            for name, qty, price, acc_code, tax_names in lines:
                acc = find_acc(acc_code)
                if not acc:
                    acc = find_acc('3001') if move_type == 'out_invoice' else find_acc('4010')
                if not acc:
                    continue
                taxes = AccountTax
                for tn in tax_names:
                    t = find_tax(tn)
                    if t:
                        taxes |= t
                inv_lines.append((0, 0, {
                    'name': name,
                    'quantity': qty,
                    'price_unit': price,
                    'account_id': acc.id,
                    'tax_ids': [(6, 0, taxes.ids)],
                }))
            if not inv_lines:
                return None
            move = AccountMove.create({
                'move_type': move_type,
                'journal_id': jrnl.id,
                'partner_id': partner.id,
                'invoice_date': date_str,
                'date': date_str,
                'invoice_line_ids': inv_lines,
                'ref': 'DEMO-' + date_str.replace('-', ''),
            })
            moves_to_post.append(move)
            return move

        # ===== May 2026 =====
        _logger.info("  Creating May 2026 demo entries...")

        # Ruta 05/10: Domestisk försäljning 25% moms
        tax_mp1 = find_tax('MP1')
        tax_i = find_tax('I')
        tax_i12 = find_tax('I12')
        tax_i6 = find_tax('I6')
        tax_mp2 = find_tax('MP2')
        tax_mp3 = find_tax('MP3')

        create_invoice('out_invoice', '2026-05-05', [
            ('Konsulttjänster AB', 1, 80000, '3001', ['MP1']),
        ], partner_id=partner)

        # Ruta 11: Utgående moms 12%
        create_invoice('out_invoice', '2026-05-08', [
            ('Livsmedel', 1, 20000, '3001', ['MP2']),
        ], partner_id=partner)

        # Ruta 12: Utgående moms 6%
        create_invoice('out_invoice', '2026-05-10', [
            ('Tidningsprenumeration', 1, 10000, '3001', ['MP3']),
        ], partner_id=partner)

        # Ruta 35: Försäljning varor till EU (exempt)
        create_invoice('out_invoice', '2026-05-12', [
            ('Export varor EU', 1, 50000, '3106', []),
        ], partner_id=partner_eu)

        # Ruta 39: Försäljning tjänster till EU (reverse charge)  
        create_invoice('out_invoice', '2026-05-14', [
            ('IT-konsult EU', 1, 30000, '3001', []),
        ], partner_id=partner_eu)

        # Ruta 48: Ingående moms 25%
        create_invoice('in_invoice', '2026-05-06', [
            ('Kontorsmaterial', 1, 30000, '4010', ['I']),
        ], partner_id=partner)

        # Ingående moms 12%
        create_invoice('in_invoice', '2026-05-09', [
            ('Livsmedel inköp', 1, 10000, '4010', ['I12']),
        ], partner_id=partner)

        # Ruta 20: Inköp varor från EU (reverse charge)
        create_invoice('in_invoice', '2026-05-15', [
            ('Maskindelar EU', 1, 60000, '4515', []),
        ], partner_id=partner_eu)

        # Ruta 21: Inköp tjänster från EU (reverse charge)
        create_invoice('in_invoice', '2026-05-18', [
            ('Molntjänst EU', 1, 25000, '4535', []),
        ], partner_id=partner_eu)

        # Ruta 22: Inköp tjänster utanför EU (reverse charge)
        create_invoice('in_invoice', '2026-05-20', [
            ('Mjukvarulicens USA', 1, 20000, '4535', []),
        ], partner_id=partner_us)

        # Ruta 50: Import
        create_invoice('in_invoice', '2026-05-25', [
            ('Elektronik import', 1, 35000, '4545', []),
        ], partner_id=partner_us)

        # ===== June 2026 =====
        _logger.info("  Creating June 2026 demo entries...")

        create_invoice('out_invoice', '2026-06-03', [
            ('Projekt fas 2', 1, 95000, '3001', ['MP1']),
        ], partner_id=partner)

        create_invoice('out_invoice', '2026-06-07', [
            ('Restaurangtjänster', 1, 15000, '3001', ['MP2']),
        ], partner_id=partner)

        create_invoice('out_invoice', '2026-06-12', [
            ('Böcker', 1, 8000, '3001', ['MP3']),
        ], partner_id=partner)

        # Ruta 36: Försäljning utanför EU
        create_invoice('out_invoice', '2026-06-10', [
            ('Export varor USA', 1, 45000, '3105', []),
        ], partner_id=partner_us)

        # Ruta 35 (igen): EU-varor
        create_invoice('out_invoice', '2026-06-15', [
            ('Leverans maskiner EU', 1, 70000, '3106', []),
        ], partner_id=partner_eu)

        create_invoice('in_invoice', '2026-06-05', [
            ('IT-utrustning', 1, 45000, '4010', ['I']),
        ], partner_id=partner)

        create_invoice('in_invoice', '2026-06-08', [
            ('Hotelltjänster', 1, 12000, '4010', ['I12']),
        ], partner_id=partner)

        create_invoice('in_invoice', '2026-06-14', [
            ('Råvaror EU', 1, 55000, '4515', []),
        ], partner_id=partner_eu)

        create_invoice('in_invoice', '2026-06-18', [
            ('Konsulttjänster EU', 1, 30000, '4535', []),
        ], partner_id=partner_eu)

        create_invoice('in_invoice', '2026-06-22', [
            ('Webbtjänster UK', 1, 18000, '4535', []),
        ], partner_id=partner_us)

        # Post all moves
        for move in moves_to_post:
            try:
                move.action_post()
            except Exception as e:
                _logger.warning("Could not post demo move %s: %s", move.ref, e)

        _logger.info("Created %d demo journal entries for VAT declarations", len(moves_to_post))
        return True


class mis_report_instance(models.Model):
    _inherit = 'mis.report.instance'
    # ~ Should be one2one. account.vat.declaration should have one unique mis.report.instance. This is to insure that the instance created also gets deleted when the account.vat.declaration does.
    account_vat_declaration_id = fields.One2many(comodel_name='account.vat.declaration', inverse_name ='generated_mis_report_id', string="account vat decaration id")

    @api.model
    def _create_default_instances(self):
        """Create default MIS report instances if they don't already exist.
        Called from l10n_se_mis data files to avoid UniqueViolation errors."""
        Report = self.env['mis.report']

        def _ensure_instance(xmlid, report_xmlid, name, **kwargs):
            existing = self.env.ref(xmlid, raise_if_not_found=False)
            if existing:
                return existing
            report = self.env.ref(report_xmlid, raise_if_not_found=False)
            if not report:
                return None
            vals = {'name': name, 'report_id': report.id, 'target_move': 'posted'}
            vals.update(kwargs)
            instance = self.create(vals)
            # Register the XML-ID for the created record
            module, _, xid = xmlid.partition('.')
            self.env['ir.model.data'].create({
                'module': module,
                'name': xid,
                'model': self._name,
                'res_id': instance.id,
                'noupdate': True,
            })
            return instance

        # Resultaträkning
        inst1 = _ensure_instance(
            'l10n_se_mis.mis_report_instance_resultatrakning',
            'l10n_se_mis.report_rr',
            'Resultaträkning',
        )
        if inst1:
            period_model = self.env['mis.report.instance.period']
            if not period_model.search_count([
                ('report_instance_id', '=', inst1.id),
                ('name', '=', 'Current year'),
            ]):
                period_model.create([{
                    'name': 'Current year',
                    'report_instance_id': inst1.id,
                    'mode': 'relative',
                    'type': 'y',
                    'offset': 0,
                    'duration': 1,
                    'sequence': 1,
                }, {
                    'name': 'Previous year',
                    'report_instance_id': inst1.id,
                    'mode': 'relative',
                    'type': 'y',
                    'offset': -1,
                    'duration': 1,
                    'sequence': 2,
                }])

        # Resultaträkning (kompakt)
        inst2 = _ensure_instance(
            'l10n_se_mis.mis_report_instance_resultatrakning_kompakt',
            'l10n_se_mis.report_rr_compact',
            'Resultaträkning (kompakt)',
            no_auto_expand_accounts=True,
        )
        if inst2:
            period_model = self.env['mis.report.instance.period']
            if not period_model.search_count([
                ('report_instance_id', '=', inst2.id),
                ('name', '=', 'Current year'),
            ]):
                period_model.create([{
                    'name': 'Current year',
                    'report_instance_id': inst2.id,
                    'mode': 'relative',
                    'type': 'y',
                    'offset': 0,
                    'duration': 1,
                    'sequence': 1,
                }, {
                    'name': 'Previous year',
                    'report_instance_id': inst2.id,
                    'mode': 'relative',
                    'type': 'y',
                    'offset': -1,
                    'duration': 1,
                    'sequence': 2,
                }])

        return True




