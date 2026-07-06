# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<http://vertel.se>).
#
##############################################################################

from odoo import models, fields, api, _
from lxml import etree
import base64
import logging
import io
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict

_logger = logging.getLogger(__name__)

# Age-based employer fee percentages (2024-2026)
# Source: Skatteverket
EMPLOYER_FEE_RATES = {
    'full': 0.3142,          # <65 år — full arbetsgivaravgift 31.42%
    'vaxa': 0.1021,          # Växa-stöd (första anställd) 10.21%
    'alderspension': 0.1636, # 66-79 år — endast ålderspension 16.36%
    'sarskild_loneskatt': 0.0615,  # ≥80 år — särskild löneskatt 6.15%
}

# AGI XML DTD reference (same DTD 6.0 as momsdeklaration)
ESKD_DTD = '<?xml version="1.0" encoding="ISO-8859-1"?>\n' \
           '<!DOCTYPE eSKDUpload PUBLIC "-//Skatteverket, Sweden//DTD ' \
           'Skatteverket eSKDUpload-DTD Version 6.0//SV" ' \
           '"https://www.skatteverket.se/ESKD">'


class AGIDeclarationLine(models.Model):
    """One row per employee in an AGI declaration.

    Maps salary data to SKV boxes (rutor) 50-82.
    """
    _name = 'account.agi.declaration.line'
    _description = 'AGI Declaration Line (per employee)'
    _order = 'employee_id'

    agi_id = fields.Many2one(
        'account.agi.declaration', string='AGI Declaration',
        required=True, ondelete='cascade', index=True,
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Employee',
        required=True, index=True,
    )
    personal_number = fields.Char(
        string='Personal Number',
        related='employee_id.identification_id',
        store=True, readonly=False,
        help='Swedish personal number (YYMMDD-XXXX)',
    )
    age_category = fields.Selection(
        selection=[
            ('full', 'Under 65 — Full arbetsgivaravgift'),
            ('vaxa', 'Växa-stöd (first employee)'),
            ('alderspension', '66-79 years — Only ålderspension'),
            ('sarskild_loneskatt', '80+ years — Särskild löneskatt'),
        ],
        string='Age Category', compute='_compute_age_category', store=True,
    )

    # SKV Box 50-62: Employer fee basis and amounts
    r50_bruttolon = fields.Monetary(string='Ruta 50: Bruttolön', currency_field='currency_id')
    r51_formaner = fields.Monetary(string='Ruta 51: Förmåner', currency_field='currency_id')
    r52_avdrag = fields.Monetary(string='Ruta 52: Avdrag', currency_field='currency_id')

    # Full employer fee (31.42%)
    r55_full_avg_underlag = fields.Monetary(string='Ruta 55: Underlag full avgift', currency_field='currency_id')
    r56_full_avg = fields.Monetary(string='Ruta 56: Full arbetsgivaravgift', currency_field='currency_id')

    # Växa-stöd (10.21%)
    r57_vaxa_underlag = fields.Monetary(string='Ruta 57: Underlag växa-stöd', currency_field='currency_id')
    r58_vaxa_avg = fields.Monetary(string='Ruta 58: Växa-stöd avgift', currency_field='currency_id')

    # Ålderspension (16.36%)
    r59_aldersp_underlag = fields.Monetary(string='Ruta 59: Underlag ålderspension', currency_field='currency_id')
    r60_aldersp_avg = fields.Monetary(string='Ruta 60: Ålderspensionsavgift', currency_field='currency_id')

    # Särskild löneskatt (6.15%)
    r61_sl_aldre_underlag = fields.Monetary(string='Ruta 61: Underlag särskild löneskatt', currency_field='currency_id')
    r62_sl_aldre_avg = fields.Monetary(string='Ruta 62: Särskild löneskatt', currency_field='currency_id')

    # SKV Box 81-82: Tax withholding
    r81_skatteavdrag_underlag = fields.Monetary(string='Ruta 81: Underlag skatteavdrag', currency_field='currency_id')
    r82_avdragen_skatt = fields.Monetary(string='Ruta 82: Avdragen preliminärskatt', currency_field='currency_id')

    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='agi_id.currency_id', store=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        related='agi_id.company_id', store=True,
    )

    @api.depends('employee_id', 'employee_id.birthday')
    def _compute_age_category(self):
        """Determine age category for employer fee calculation."""
        today = date.today()
        for line in self:
            if not line.employee_id.birthday:
                line.age_category = 'full'
                continue
            age = relativedelta(today, line.employee_id.birthday).years
            if age >= 80:
                line.age_category = 'sarskild_loneskatt'
            elif age >= 66:
                line.age_category = 'alderspension'
            else:
                # Check for Växa-stöd eligibility
                if line.agi_id and line.agi_id._is_vaxa_eligible(line.employee_id):
                    line.age_category = 'vaxa'
                else:
                    line.age_category = 'full'

    def _calculate_employer_fees(self):
        """Calculate employer fees (rutor 55-62) based on age category."""
        self.ensure_one()
        rate_map = {
            'full': {'underlag_field': 'r55_full_avg_underlag', 'avgift_field': 'r56_full_avg', 'rate': EMPLOYER_FEE_RATES['full']},
            'vaxa': {'underlag_field': 'r57_vaxa_underlag', 'avgift_field': 'r58_vaxa_avg', 'rate': EMPLOYER_FEE_RATES['vaxa']},
            'alderspension': {'underlag_field': 'r59_aldersp_underlag', 'avgift_field': 'r60_aldersp_avg', 'rate': EMPLOYER_FEE_RATES['alderspension']},
            'sarskild_loneskatt': {'underlag_field': 'r61_sl_aldre_underlag', 'avgift_field': 'r62_sl_aldre_avg', 'rate': EMPLOYER_FEE_RATES['sarskild_loneskatt']},
        }
        info = rate_map.get(self.age_category, rate_map['full'])
        # Underlag = bruttolön + förmåner - avdrag
        underlag = (self.r50_bruttolon or 0.0) + (self.r51_formaner or 0.0) - (self.r52_avdrag or 0.0)
        self[info['underlag_field']] = max(0.0, underlag)
        self[info['avgift_field']] = round(underlag * info['rate'], 0)

    def _calculate_tax_basis(self):
        """Set tax withholding basis (ruta 81) from salary data."""
        self.ensure_one()
        self.r81_skatteavdrag_underlag = max(0.0, (self.r50_bruttolon or 0.0) + (self.r51_formaner or 0.0) - (self.r52_avdrag or 0.0))


class AGIDeclaration(models.Model):
    """AGI (Arbetsgivardeklaration — Individuppgifter).

    Inherits from account.declaration for state machine, SKV API infrastructure,
    and calendar event handling. One declaration per month per company.
    """
    _name = 'account.agi.declaration'
    _inherit = ['account.declaration', 'mail.thread']
    _description = 'AGI Declaration (Individuppgifter)'
    _order = 'date_start desc'

    _report_name = 'AGI'

    line_ids = fields.One2many(
        'account.agi.declaration.line', 'agi_id',
        string='Employee Lines',
        copy=True,
    )
    agi_file = fields.Binary(string='AGI eSKD XML', readonly=True, copy=False)
    agi_file_name = fields.Char(string='Filename', compute='_compute_agi_file_name')

    employee_count = fields.Integer(
        string='Employees', compute='_compute_summary', store=True,
    )
    total_salary = fields.Monetary(
        string='Total Gross Salary', compute='_compute_summary', store=True,
        currency_field='currency_id',
    )
    total_employer_fee = fields.Monetary(
        string='Total Employer Fee', compute='_compute_summary', store=True,
        currency_field='currency_id',
    )
    total_tax_withheld = fields.Monetary(
        string='Total Tax Withheld', compute='_compute_summary', store=True,
        currency_field='currency_id',
    )
    total_to_pay = fields.Monetary(
        string='Total to Pay', compute='_compute_summary', store=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # Source: either linked payslip run or manual entry
    payslip_run_id = fields.Many2one(
        'hr.payslip.run', string='Payslip Run',
        help='Link to the salary run this AGI is based on.',
    )

    @api.onchange('date_start', 'date_stop')
    def onchange_date(self):
        super().onchange_date()
        self.name = 'AGI %s – %s' % (self.date_start, self.date_stop)

    @api.depends('line_ids')
    def _compute_summary(self):
        for rec in self:
            rec.employee_count = len(rec.line_ids)
            rec.total_salary = sum(line.r50_bruttolon or 0.0 for line in rec.line_ids)
            rec.total_employer_fee = sum(
                (line.r56_full_avg or 0.0) + (line.r58_vaxa_avg or 0.0) +
                (line.r60_aldersp_avg or 0.0) + (line.r62_sl_aldre_avg or 0.0)
                for line in rec.line_ids
            )
            rec.total_tax_withheld = sum(line.r82_avdragen_skatt or 0.0 for line in rec.line_ids)
            rec.total_to_pay = rec.total_employer_fee + rec.total_tax_withheld

    def _compute_agi_file_name(self):
        for rec in self:
            org_nr = rec.company_id.vat or 'UNKNOWN'
            period = rec.date_start.strftime('%Y%m') if rec.date_start else '000000'
            rec.agi_file_name = 'AGI_%s_%s.xml' % (org_nr, period)

    # ------------------------------------------------------------------
    # Calculation: aggregate payslip data into AGI lines
    # ------------------------------------------------------------------

    def action_calculate(self):
        """Calculate AGI lines from linked payslip run or account moves."""
        self.ensure_one()
        if self.state not in ('draft', 'confirmed'):
            raise UserError(_('Cannot recalculate AGI in state %s.') % self.state)

        self.line_ids.unlink()

        if self.payslip_run_id:
            self._calculate_from_payslip_run()
        else:
            self._calculate_from_account_moves()

        # Calculate employer fees per line
        for line in self.line_ids:
            line._calculate_employer_fees()
            line._calculate_tax_basis()

        self.state = 'confirmed'

    def _calculate_from_payslip_run(self):
        """Aggregate payslip data per employee and create AGI lines.

        Maps salary rule codes to AGI boxes:
            bl/gl (bruttolön)        -> r50, r81
            förmån (benefits)        -> r51
            avdrag (deductions)      -> r52
            sa (arbetsgivaravgift)   -> r56/58/60/62 (age-based)
            total_skatt (tax)        -> r82
        """
        self.ensure_one()
        if not self.payslip_run_id:
            return

        # Group by employee
        employee_data = defaultdict(lambda: {
            'r50': 0.0, 'r51': 0.0, 'r52': 0.0, 'r82': 0.0,
        })

        for slip in self.payslip_run_id.slip_ids.filtered(lambda s: s.state in ('done', 'paid')):
            emp = slip.employee_id
            emp_data = employee_data[emp.id]
            emp_data['employee'] = emp

            for line in slip.line_ids:
                code = (line.salary_rule_id.code or '').lower() if line.salary_rule_id else ''
                amount = abs(line.total) if line.total else 0.0

                if code in ('bl', 'gl', 'bruttolon', 'grundlon', 'manadslon', 'timlon'):
                    emp_data['r50'] += amount
                elif code in ('forman', 'benefit') or 'forman' in code:
                    emp_data['r51'] += amount
                elif code in ('avdrag', 'deduction') or 'avdrag' in code:
                    emp_data['r52'] += amount
                elif code in ('skatt', 'total_skatt', 'preliminar_skatt'):
                    emp_data['r82'] += amount

        # Create AGI lines
        for emp_id, data in employee_data.items():
            if data['r50'] <= 0:
                continue
            self.env['account.agi.declaration.line'].create({
                'agi_id': self.id,
                'employee_id': data['employee'].id,
                'personal_number': data['employee'].identification_id,
                'r50_bruttolon': data['r50'],
                'r51_formaner': data['r51'],
                'r52_avdrag': data['r52'],
                'r81_skatteavdrag_underlag': data['r50'] + data['r51'] - data['r52'],
                'r82_avdragen_skatt': data['r82'],
            })

    def _calculate_from_account_moves(self):
        """Fallback: aggregate from account.move lines for salary accounts.

        Uses account codes in range 7000-7699 (personalkostnader) and
        2700-2799 (personalens skatter) to estimate AGI data.
        """
        self.ensure_one()
        salary_accounts = self.env['account.account'].search([
            ('code', '>=', '7000'), ('code', '<=', '7699'),
            ('company_id', '=', self.company_id.id),
        ])
        tax_accounts = self.env['account.account'].search([
            ('code', '>=', '2700'), ('code', '<=', '2799'),
            ('company_id', '=', self.company_id.id),
        ])

        if not salary_accounts:
            _logger.warning('No salary accounts (7000-7699) found for company %s', self.company_id.name)
            return

        # Get account moves in period
        domain = [
            ('date', '>=', self.date_start),
            ('date', '<=', self.date_stop),
            ('state', '=', 'posted'),
            ('account_id', 'in', (salary_accounts + tax_accounts).ids),
            ('company_id', '=', self.company_id.id),
        ]

        # This is a simplified fallback — real AGI requires per-employee data
        _logger.warning(
            'AGI calculated from account moves (no payslip run linked). '
            'This is an approximation — use payslip integration for accurate data.'
        )
        # Create a single aggregated line as placeholder
        self.env['account.agi.declaration.line'].create({
            'agi_id': self.id,
            'employee_id': False,
            'personal_number': 'AGGREGATED',
            'r50_bruttolon': self._get_total_from_accounts(salary_accounts),
            'r81_skatteavdrag_underlag': self._get_total_from_accounts(salary_accounts),
            'r82_avdragen_skatt': self._get_total_from_accounts(tax_accounts),
        })

    def _get_total_from_accounts(self, accounts):
        """Get total debit/credit from account moves in period."""
        if not accounts:
            return 0.0
        moves = self.env['account.move.line'].search([
            ('date', '>=', self.date_start),
            ('date', '<=', self.date_stop),
            ('state', '=', 'posted'),
            ('account_id', 'in', accounts.ids),
            ('company_id', '=', self.company_id.id),
        ])
        return abs(sum(moves.mapped('debit')) - sum(moves.mapped('credit')))

    def _is_vaxa_eligible(self, employee):
        """Check if an employee qualifies for Växa-stöd.

        Växa-stöd applies to the first employee hired by a sole trader
        or a company that has not had employees before.
        Simplified check: first salaried employee in the system.
        """
        self.ensure_one()
        # Check if this is the only active employee receiving salary
        all_agi_lines = self.env['account.agi.declaration.line'].search([
            ('company_id', '=', self.company_id.id),
            ('agi_id', '!=', self.id),
            ('r50_bruttolon', '>', 0),
        ])
        return len(all_agi_lines.mapped('employee_id')) == 0

    # ------------------------------------------------------------------
    # XML Generation
    # ------------------------------------------------------------------

    def action_generate_xml(self):
        """Generate eSKD XML file for AGI submission."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('No employee data to generate AGI XML. Run Calculate first.'))

        xml_bytes = self._generate_eskd_xml()
        self.agi_file = base64.b64encode(xml_bytes)
        self.state = 'confirmed'
        _logger.info('AGI XML generated for %s: %d employees', self.name, self.employee_count)

    def _generate_eskd_xml(self):
        """Build eSKD XML document following Skatteverket's DTD 6.0."""
        root = etree.Element('eSKDUpload', Version='6.0')

        org_nr = etree.SubElement(root, 'OrgNr')
        vat = (self.company_id.vat or '').replace('SE', '').replace('-', '')
        org_nr.text = vat[:10]

        agd = etree.SubElement(root, 'Arbetsgivardeklaration')

        period = etree.SubElement(agd, 'Period')
        period.text = self.date_start.strftime('%Y%m') if self.date_start else ''

        for line in self.line_ids.filtered(lambda l: l.r50_bruttolon > 0):
            anstalld = etree.SubElement(agd, 'Anstalld')

            pnr = etree.SubElement(anstalld, 'PersonNr')
            pnr.text = (line.personal_number or '').replace('-', '')[:12]

            if line.r50_bruttolon:
                etree.SubElement(anstalld, 'Ruta50').text = str(int(line.r50_bruttolon))
            if line.r51_formaner:
                etree.SubElement(anstalld, 'Ruta51').text = str(int(line.r51_formaner))
            if line.r52_avdrag:
                etree.SubElement(anstalld, 'Ruta52').text = str(int(line.r52_avdrag))

            # Employer fee boxes based on age category
            if line.age_category == 'full' and line.r55_full_avg_underlag:
                etree.SubElement(anstalld, 'Ruta55').text = str(int(line.r55_full_avg_underlag))
                etree.SubElement(anstalld, 'Ruta56').text = str(int(line.r56_full_avg or 0))
            elif line.age_category == 'vaxa' and line.r57_vaxa_underlag:
                etree.SubElement(anstalld, 'Ruta57').text = str(int(line.r57_vaxa_underlag))
                etree.SubElement(anstalld, 'Ruta58').text = str(int(line.r58_vaxa_avg or 0))
            elif line.age_category == 'alderspension' and line.r59_aldersp_underlag:
                etree.SubElement(anstalld, 'Ruta59').text = str(int(line.r59_aldersp_underlag))
                etree.SubElement(anstalld, 'Ruta60').text = str(int(line.r60_aldersp_avg or 0))
            elif line.age_category == 'sarskild_loneskatt' and line.r61_sl_aldre_underlag:
                etree.SubElement(anstalld, 'Ruta61').text = str(int(line.r61_sl_aldre_underlag))
                etree.SubElement(anstalld, 'Ruta62').text = str(int(line.r62_sl_aldre_avg or 0))

            if line.r81_skatteavdrag_underlag:
                etree.SubElement(anstalld, 'Ruta81').text = str(int(line.r81_skatteavdrag_underlag))
            if line.r82_avdragen_skatt:
                etree.SubElement(anstalld, 'Ruta82').text = str(int(line.r82_avdragen_skatt))

        xml_declaration = b'<?xml version="1.0" encoding="ISO-8859-1"?>\n'
        # We use UTF-8 internally but the DTD expects ISO-8859-1
        tree = etree.ElementTree(root)
        output = io.BytesIO()
        tree.write(output, encoding='ISO-8859-1', xml_declaration=True,
                   doctype='<!DOCTYPE eSKDUpload PUBLIC "-//Skatteverket, Sweden//DTD '
                           'Skatteverket eSKDUpload-DTD Version 6.0//SV" '
                           '"https://www.skatteverket.se/ESKD">')
        return output.getvalue()

    # ------------------------------------------------------------------
    # SKV API submission (reuses l10n_se_tax_report infrastructure)
    # ------------------------------------------------------------------

    def action_send_to_skv(self):
        """Submit AGI to Skatteverket via API."""
        self.ensure_one()
        if not self.agi_file:
            self.action_generate_xml()

        company = self.company_id
        access_token = self._get_skv_access_token(company)
        if not access_token:
            raise UserError(_(
                'Could not obtain access token for Skatteverket API. '
                'Configure in Accounting > Configuration > Skatteverket API.'
            ))

        api_url = self.company_id.skv_agi_api_url or \
            'https://api.skatteverket.se/arbetsgivare/v2/deklaration/individuppgift'

        try:
            response = self._post_to_skv(api_url, access_token, self.agi_file)
            self.skv_api_status = 'sent'
            self.skv_response = response
            self.state = 'done'
            self.message_post(body=_('AGI submitted to Skatteverket successfully.'))
        except Exception as e:
            self.skv_api_status = 'error'
            self.skv_response = str(e)
            self.message_post(body=_('AGI submission failed: %s') % e)
            raise UserError(_('AGI submission failed: %s') % e)

    def _post_to_skv(self, url, token, xml_data):
        """POST XML to Skatteverket API. Override for production use."""
        import requests
        response = requests.post(
            url,
            data=base64.b64decode(xml_data) if isinstance(xml_data, bytes) else xml_data,
            headers={
                'Authorization': 'Bearer %s' % token,
                'Content-Type': 'application/xml; charset=ISO-8859-1',
            },
            timeout=30,
        )
        if response.status_code not in (200, 201, 202):
            raise UserError(_('SKV API returned %d: %s') % (response.status_code, response.text[:500]))
        return response.text

    # ------------------------------------------------------------------
    # Cron: auto-create monthly AGI
    # ------------------------------------------------------------------

    @api.model
    def _cron_create_agi(self):
        """Cron job: create AGI declarations for all companies for the previous month."""
        today = date.today()
        # Previous month
        period_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        period_stop = today.replace(day=1) - timedelta(days=1)

        companies = self.env['res.company'].search([])
        for company in companies:
            existing = self.search([
                ('company_id', '=', company.id),
                ('date_start', '=', period_start),
                ('date_stop', '=', period_stop),
            ])
            if existing:
                continue
            self.with_company(company).create({
                'company_id': company.id,
                'date_start': period_start,
                'date_stop': period_stop,
                'state': 'draft',
            })

    # ------------------------------------------------------------------
    # KU10 (Kontrolluppgift) generation
    # ------------------------------------------------------------------

    def action_generate_ku10(self):
        """Generate KU10 (Kontrolluppgift) from AGI data.

        KU10 reports total salary and tax for each employee to Skatteverket.
        Uses the same AGI data aggregated to a yearly view.
        """
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('No data for KU10. Run Calculate first.'))

        ku_lines = []
        for line in self.line_ids.filtered(lambda l: l.r50_bruttolon > 0):
            ku_lines.append({
                'employee_id': line.employee_id.id,
                'personal_number': line.personal_number,
                'bruttolon': line.r50_bruttolon,
                'formaner': line.r51_formaner or 0.0,
                'avdragen_skatt': line.r82_avdragen_skatt or 0.0,
                'arbetsgivaravgift': (
                    (line.r56_full_avg or 0.0) + (line.r58_vaxa_avg or 0.0) +
                    (line.r60_aldersp_avg or 0.0) + (line.r62_sl_aldre_avg or 0.0)
                ),
            })

        # Create KU10 XML (simplified — real implementation needs full SKV schema)
        root = etree.Element('Kontrolluppgifter', Ar='%d' % self.date_start.year)
        for ku in ku_lines:
            entry = etree.SubElement(root, 'KU10')
            etree.SubElement(entry, 'Personnummer').text = (ku['personal_number'] or '').replace('-', '')[:12]
            etree.SubElement(entry, 'KontantBruttolon').text = str(int(ku['bruttolon']))
            etree.SubElement(entry, 'Formaner').text = str(int(ku['formaner']))
            etree.SubElement(entry, 'AvdragenSkatt').text = str(int(ku['avdragen_skatt']))
            etree.SubElement(entry, 'Arbetsgivaravgift').text = str(int(ku['arbetsgivaravgift']))

        output = io.BytesIO()
        tree = etree.ElementTree(root)
        tree.write(output, encoding='UTF-8', xml_declaration=True)
        self.message_post(
            body=_('KU10 generated for %d employees.') % len(ku_lines),
            attachment_ids=[self.env['ir.attachment'].create({
                'name': 'KU10_%s.xml' % self.date_start.strftime('%Y%m'),
                'datas': base64.b64encode(output.getvalue()),
                'res_model': self._name,
                'res_id': self.id,
            }).id],
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
        }
