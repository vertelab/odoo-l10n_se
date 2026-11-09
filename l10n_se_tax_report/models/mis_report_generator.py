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

    # The declaration now points at an account.report instead of a MIS
    # instance. Kept side by side during the migration: new declarations get
    # generated_report_id, old ones keep their MIS instance readable.
    generated_report_id = fields.Many2one(
        comodel_name='account.report', string='Generated Report',
        ondelete='restrict', readonly=True,
        help='The account.report this declaration was computed from.')
    generated_mis_report_id = fields.Many2one(
        comodel_name='mis.report.instance', string='mis_report_instance',
        ondelete='cascade', readonly=True,
        help='Legacy: the MIS Builder instance used before the migration. '
             'Readable for historical declarations; never written any more.')

    # The box amounts, so the declaration is self-describing after the switch.
    box_05 = fields.Float(string='05 Momspliktig försäljning', readonly=True)
    box_10 = fields.Float(string='10 Utgående moms 25 %', readonly=True)
    box_11 = fields.Float(string='11 Utgående moms 12 %', readonly=True)
    box_12 = fields.Float(string='12 Utgående moms 6 %', readonly=True)
    box_30 = fields.Float(string='30 Utgående moms omvänd 25 %', readonly=True)
    box_31 = fields.Float(string='31 Utgående moms omvänd 12 %', readonly=True)
    box_32 = fields.Float(string='32 Utgående moms omvänd 6 %', readonly=True)
    box_48 = fields.Float(string='48 Ingående moms', readonly=True)
    
    @api.depends('name')
    def _change_mis_report_name(self):
        for dec in self:
            # Only historical declarations still carry a MIS instance.
            if dec.generated_mis_report_id:
                dec.generated_mis_report_id.name = dec.name
    
    @api.depends('target_move','name','accounting_yearend','company_id',
                 'generated_report_id','date_start','date_stop')
    def _vat(self):
         for decl in self:
             decl.vat_momsutg = 0
             decl.vat_momsingavdr = 0
             decl.vat_momsbetala  = 0
             decl.box_05 = decl.box_10 = decl.box_11 = decl.box_12 = 0.0
             decl.box_30 = decl.box_31 = decl.box_32 = decl.box_48 = 0.0
             if decl.date_start and decl.date_stop:
                ##Faktura vs kontant method betyder ifall man tar fakturor som är betalda eller inte.
                ##Det är betalningens datums som ska användas istället.
                ##Behöver återimplementeras på något sätt.
                amounts = decl._get_box_amounts()
                decl.box_05 = amounts.get('se_05', 0.0)
                decl.box_10 = amounts.get('se_10', 0.0)
                decl.box_11 = amounts.get('se_11', 0.0)
                decl.box_12 = amounts.get('se_12', 0.0)
                decl.box_30 = amounts.get('se_30', 0.0)
                decl.box_31 = amounts.get('se_31', 0.0)
                decl.box_32 = amounts.get('se_32', 0.0)
                decl.box_48 = amounts.get('se_48', 0.0)

                # Output VAT is boxes 10-12 plus the reverse-charge 30-32.
                # Import VAT (60-62) is deliberately NOT included here: it is
                # deductible in box 48 and would otherwise be counted twice.
                output = ['se_10', 'se_11', 'se_12', 'se_30', 'se_31', 'se_32']
                decl.vat_momsutg = abs(int(round(sum(
                    amounts.get(code, 0.0) for code in output))))
                decl.vat_momsingavdr = abs(int(round(amounts.get('se_48', 0.0))))
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
            if momsskuld and momsfordran:
                entry = self.env['account.move'].create({
                    'journal_id': moms_journal.id,
                    #'period_id': self.period_start.id,
                    'date': fields.Date.today(),
                    'ref': u'Momsdeklaration',
                    'partner_id': self.env.ref(
                        'l10n_se_tax_report.res_partner-SKV').id,
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
                    # as the balancing line against the VAT settlement account.
                    #
                    # Swedish standard (BAS): the net VAT (Ruta 49) is cleared
                    # against 2650 "Redovisningskonto för moms" — NOT directly
                    # against 1630 "Skattekonto". The transfer to the tax account
                    # is a separate step, see _create_tax_account_transfer().
                    if moms_diff != 0.0:
                        settlement_account = (
                            momsskuld if moms_diff > 0.0 else momsfordran)
                        move_line_list.append((0, 0, {
                            'name': settlement_account.name,
                            'account_id': settlement_account.id,
                            'partner_id': self.env.ref(
                                'l10n_se_tax_report.res_partner-SKV').id,
                            'debit': abs(moms_diff) if moms_diff < 0.0 else 0.0,
                            'credit': moms_diff if moms_diff > 0.0 else 0.0,
                            'move_id': entry.id,
                        }))
                    entry.write({
                        'line_ids': move_line_list,
                    })
                    self.write({'move_id': entry.id})
                    entry.vat_declaration_id = self.id
            else:
                raise UserError(_('You are missing either a credit account or a debit account on the VAT journal, please add these'))

        # Step 2: move the VAT debt from 2650 to the tax account (1630).
        # Runs automatically when the declaration is confirmed (calculate()).
        self._create_tax_account_transfer()

    def _create_tax_account_transfer(self):
        """Move the net VAT from 2650 to 1630 (Skattekonto).

        Swedish standard (BAS):
            1. Period:      utgående moms 261x / ingående moms 264x
            2. Declaration: net against 2650 (Redovisningskonto för moms)
            3. Payment:     2650 <-> 1630 (Skattekonto)

        Step 2 is done by calculate(). This method performs step 3 so that the
        VAT debt lands on 1630, where the payment order can pick it up and
        where l10n_se_tax_account reconciles it against Skatteverket.

        Idempotent: does nothing if the transfer entry already exists.
        """
        for rec in self:
            if rec.skattekonto_move_id:
                continue
            amount = rec.vat_momsbetala
            if not amount:
                continue

            moms_journal = self.env['account.journal'].search([
                ('company_id', '=', rec.company_id.id),
                ('name', '=', 'Momsjournal'),
                ('type', '=', 'general'),
                ('code', '=', 'MOMS'),
            ], limit=1)
            if not moms_journal:
                raise UserError(_(
                    'Configure your tax declaration journal! It needs to be '
                    'named Momsjournal, be of the general/miscellaneous type, '
                    'and have MOMS as the code.'))

            momsskuld = moms_journal.default_credit_account_id
            momsfordran = moms_journal.default_debit_account_id
            skattekonto = self.env['account.account'].search([
                ('company_ids', 'in', [rec.company_id.id]),
                ('code', '=', '1630'),
            ], limit=1)
            if not (momsskuld and momsfordran and skattekonto):
                raise UserError(_(
                    'You are missing either a credit account, debit account '
                    'or the tax account 1630, please add these'))

            skv_partner = self.env.ref('l10n_se_tax_report.res_partner-SKV')
            amount = int(round(amount))

            entry = self.env['account.move'].create({
                'journal_id': moms_journal.id,
                'date': fields.Date.today(),
                'ref': _('Momsdeklaration - överföring till skattekonto'),
                'partner_id': skv_partner.id,
            })

            if amount > 0:
                # VAT to pay: debt moves 2650 -> 1630
                vat_debit, vat_credit = 0.0, amount
                tax_debit, tax_credit = amount, 0.0
            else:
                # VAT refund: receivable moves 1630 -> 1650
                vat_debit, vat_credit = abs(amount), 0.0
                tax_debit, tax_credit = 0.0, abs(amount)

            entry.write({'line_ids': [
                (0, 0, {
                    'name': momsskuld.name if amount > 0 else momsfordran.name,
                    'account_id': (momsskuld if amount > 0 else momsfordran).id,
                    'partner_id': skv_partner.id,
                    'debit': vat_debit,
                    'credit': vat_credit,
                    'move_id': entry.id,
                }),
                (0, 0, {
                    'name': skattekonto.name,
                    'account_id': skattekonto.id,
                    'partner_id': skv_partner.id,
                    'debit': tax_debit,
                    'credit': tax_credit,
                    'move_id': entry.id,
                }),
            ]})
            entry.vat_declaration_id = rec.id
            rec.skattekonto_move_id = entry.id

                    
    def do_draft(self):
        for rec in self:
            create_eskd_xml_file = None
            super(account_vat_declaration, rec).do_draft()
            for move in rec.move_ids:
                move.vat_declaration_id = None
            rec._unlink_tax_account_transfer()

    def do_cancel(self):
        for rec in self:
            super(account_vat_declaration, rec).do_draft()
            create_eskd_xml_file = None
            for move in rec.move_ids:
                move.vat_declaration_id = None
            rec._unlink_tax_account_transfer()

    def _unlink_tax_account_transfer(self):
        """Remove the 2650 -> 1630 transfer entry, if any.

        Must run whenever the declaration is reset to draft/cancelled,
        otherwise the tax account (1630) keeps a balance that no longer
        corresponds to a declaration. Declarations created before this
        feature have no transfer entry — handled by the empty check.
        """
        for rec in self:
            move = rec.skattekonto_move_id
            if not move:
                continue
            if move.state == 'posted':
                move.button_draft()
            move.unlink()
            rec.skattekonto_move_id = False

        
    @api.model
    def _get_tax_report(self):
        """The Swedish VAT account.report this declaration is computed from."""
        self.ensure_one()
        if self.generated_report_id:
            return self.generated_report_id
        report = self.env['account.report'].search([
            ('country_id.code', '=', 'SE'),
            ('name', '=', 'skatterapport'),
        ], limit=1)
        if not report:
            raise UserError(_(
                "No Swedish tax report (account.report) is configured. "
                "Install l10n_se and l10n_se_tax_report."))
        return report

    def _get_box_amounts(self):
        """{code: amount} for every line of the Swedish VAT report."""
        self.ensure_one()
        report = self._get_tax_report()
        options = {
            'date': {
                'date_from': fields.Date.to_string(self.date_start) if self.date_start else None,
                'date_to': fields.Date.to_string(self.date_stop) if self.date_stop else None,
            },
            'company_ids': [self.company_id.id],
            'unfold_all': True,
        }
        warnings = {}
        lines = report._get_lines(options, warnings=warnings)
        amounts = {}
        for line in lines:
            code = line.get('code')
            if not code:
                continue
            columns = line.get('columns') or []
            if columns:
                amounts[code] = float(columns[0].get('no_format') or 0.0)
        return amounts

    def show_report(self):
        """Open the declaration's report in the standard report view."""
        self.ensure_one()
        report = self._get_tax_report()
        return report.open_report({
            'date': {
                'date_from': fields.Date.to_string(self.date_start) if self.date_start else None,
                'date_to': fields.Date.to_string(self.date_stop) if self.date_stop else None,
            },
            'company_ids': [self.company_id.id],
        })

    def show_mis_report(self):
        """Backwards-compatible alias for the old button name."""
        return self.show_report()

    @api.model_create_multi
    def create(self, vals_list):
        records = super(account_vat_declaration, self).create(vals_list)
        for record in records:
            if record.accounting_yearend:
                accounting_method = 'invoice'
            else:
                if not record.company_id.accounting_method:
                    raise UserError(_(
                        "Accounting method is not configured for company %s. "
                        "Set it in Accounting → Configuration → Settings.")
                        % record.company_id.name)
                accounting_method = record.company_id.accounting_method
            # Point the declaration at the account.report it is computed from.
            # The MIS instance is no longer created: generated_mis_report_id is
            # kept only so historical declarations stay readable.
            report = self.env['account.report'].search([
                ('country_id.code', '=', 'SE'),
                ('name', '=', 'skatterapport'),
            ], limit=1)
            if not report:
                raise UserError(_(
                    "No Swedish tax report (account.report) is available. "
                    "Install l10n_se and l10n_se_tax_report."))
            record.generated_report_id = report

        return records
        
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
        # Map box code -> eSKD element via the data table, so the export knows
        # nothing about MIS Builder or Swedish box numbering.
        amounts = self._get_box_amounts()
        mappings = self.env['l10n.se.eskd.mapping'].search([('active', '=', True)])
        for mapping in mappings:
            if mapping.code in ('se_49',):
                # The summary row is emitted separately as MomsBetala below.
                continue
            value = amounts.get(mapping.code, 0.0)
            if value > 0:
                tax = etree.SubElement(moms, mapping.eskd_tag)
                tax.text = str(int(round(value)))
        
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
    # KPI name -> report line code, so callers that still speak MIS keep working.
    KPI_TO_CODE = {
        'ForsMomsEjAnnan': 'se_05',
        'MomsUtgHog': 'se_10',
        'MomsUtgMedel': 'se_11',
        'MomsUtgLag': 'se_12',
        'MomsInkopUtgHog': 'se_30',
        'MomsInkopUtgMedel': 'se_31',
        'MomsInkopUtgLag': 'se_32',
        'MomsIngAvdr': 'se_48',
        'MomsImportUtgHog': 'se_60',
        'MomsImportUtgMedel': 'se_61',
        'MomsImportUtgLag': 'se_62',
    }

    def get_move_line_recordset(self, row_kpi_names):
        """Move lines behind the given boxes.

        Kept as a thin wrapper so the journal-entry creation does not have to
        change: it still asks for KPI names, but the answer now comes from the
        report's own drill-down instead of MIS Builder's.
        """
        self.ensure_one()
        report = self._get_tax_report()
        options = {
            'date': {
                'date_from': fields.Date.to_string(self.date_start) if self.date_start else None,
                'date_to': fields.Date.to_string(self.date_stop) if self.date_stop else None,
            },
            'company_ids': [self.company_id.id],
        }
        move_line_recordset = self.env['account.move.line']
        for kpi_name in (row_kpi_names or []):
            code = self.KPI_TO_CODE.get(kpi_name, kpi_name)
            line = report.line_ids.filtered(lambda l: l.code == code)
            if not line:
                _logger.warning(
                    "VAT declaration: no report line with code %s (KPI %s)",
                    code, kpi_name,
                )
                continue
            move_line_recordset |= report._get_line_drilldown_lines(line, options)
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
        url = company._get_skv_api_url('/moms/v2/deklaration')
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
