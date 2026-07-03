from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from lxml import etree
import base64
import requests
import logging
_logger = logging.getLogger(__name__)


class account_periodic_compilation(models.Model):
    _name = 'account.periodic.compilation'
    _inherit = 'account.declaration'
    _report_name = 'Periodisk sammanställning'
    _order = 'date desc'
    _description = 'Periodisk sammanställning (EU-försäljningslista)'

    line_ids = fields.One2many(
        comodel_name='account.declaration.line',
        inverse_name='periodic_compilation_id')

    invoice_ids = fields.One2many(
        comodel_name='account.move',
        inverse_name='periodic_compilation_id')

    pc_file = fields.Binary(string="Periodisk sammanställning", readonly=True)
    pc_file_name = fields.Char(string="File Name", default="periodisk_sammanstallning.xml")

    generated_mis_report_id = fields.Many2one(
        comodel_name='mis.report.instance',
        string='MIS Report Instance',
        ondelete='cascade',
        readonly=True,
    )
    report_id = fields.Many2one(
        'mis.report',
        string='Report',
        default=lambda self: self.env.company.pc_report_template_id.id
            or self.env.ref('l10n_se_mis.report_pc').id,
    )

    def _invoice_ids_count(self):
        for rec in self:
            rec.invoice_ids_count = len(rec.invoice_ids)
    invoice_ids_count = fields.Integer(compute='_invoice_ids_count')

    def _move_line_ids_count(self):
        for rec in self:
            rec.move_line_ids_count = self.env['account.move.line'].search_count([
                ('move_id.periodic_compilation_id', '=', rec.id),
            ])
    move_line_ids_count = fields.Integer(compute='_move_line_ids_count')

    @api.model
    def _calculate_pc_deadline(self, date_stop):
        """Calculate the deadline for Periodisk sammanställning (EU sales list).

        Swedish rules (ML 17 kap):
        - Deadline is the LAST DAY of the month following the period end.
          e.g. January 31 -> February 28, February 28 -> March 31
        - If the deadline falls on a weekend/holiday, next working day.
        """
        from workalendar.europe import Sweden
        cal = Sweden()
        # Last day of the month following the period end:
        # relativedelta(day=31) clips to the actual last day of the month
        deadline = date_stop + relativedelta(months=1, day=31)
        while not cal.is_working_day(deadline):
            deadline += timedelta(days=1)
        return deadline

    @api.onchange('date_start', 'date_stop')
    def _onchange_period_dates(self):
        if self.date_start and self.date_stop:
            self.name = '%s %s - %s' % (self._report_name, self.date_start, self.date_stop)
            self.date = self._calculate_pc_deadline(
                fields.Date.from_string(self.date_stop))

    @api.model
    def _generate_mis_report(self, start_date, stop_date, target_move_param,
                             name_param, company_id, report_id=None):
        """Create a MIS report instance for the given period.
        Uses the PC-specific MIS report (not the momsdeklaration report)."""
        report_instance = self.env['mis.report.instance'].create({
            'report_id': report_id
                or company_id.pc_report_template_id.id
                or self.env.ref('l10n_se_mis.report_pc').id,
            'target_move': target_move_param,
            'name': 'PC: ' + name_param,
            'company_id': company_id.id,
            'period_ids': [
                (0, 0, {
                    'name': 'p1',
                    'mode': 'fix',
                    'manual_date_from': start_date,
                    'manual_date_to': stop_date,
                }),
            ],
        })
        return report_instance

    @api.model
    def create(self, vals):
        """Ensure date and name are computed when created from code (cron, batch).
        Also create a MIS report instance for consistent data with VAT report."""
        if vals.get('date_start') and vals.get('date_stop'):
            if not vals.get('date'):
                date_stop = fields.Date.from_string(vals['date_stop'])
                vals['date'] = fields.Date.to_string(
                    self._calculate_pc_deadline(date_stop))
            if not vals.get('name'):
                vals['name'] = '%s %s - %s' % (
                    self._report_name, vals['date_start'], vals['date_stop'])
        record = super(account_periodic_compilation, self).create(vals)
        # Create MIS report instance (must be done after super() so record has company_id)
        if record.date_start and record.date_stop:
            company = record.company_id or self.env.company
            record.generated_mis_report_id = self._generate_mis_report(
                record.date_start,
                record.date_stop,
                record.target_move,
                record.name,
                company,
                report_id=record.report_id.id,
            )
        return record

    def _get_period_invoices(self):
        domain = [
            ('invoice_date', '>=', self.date_start),
            ('invoice_date', '<=', self.date_stop),
            ('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')),
        ]
        if self.target_move == 'posted':
            domain.append(('state', '=', 'posted'))
        elif self.target_move == 'draft':
            domain.append(('state', '=', 'draft'))
        return self.env['account.move'].search(domain)

    def _get_tax_by_name(self, name):
        return self.env['account.tax'].search([('name', '=', name)], limit=1)

    _EU_SERVICE_TAX_NAMES = ['FTEU']

    def _get_move_lines_for_kpi(self, kpi_name):
        """Use MIS drilldown to get account.move.line records contributing
        to a specific KPI. Returns an empty recordset if no MIS instance.
        Falls back gracefully if the MIS report or KPI is unavailable."""
        self.ensure_one()
        if not self.generated_mis_report_id:
            return self.env['account.move.line']
        try:
            mis = self.generated_mis_report_id
            if mis.period_ids:
                mis.period_ids.write({
                    'manual_date_from': self.date_start,
                    'manual_date_to': self.date_stop,
                })
            mis.write({'target_move': self.target_move})

            matrix = mis._compute_matrix()
            move_lines = self.env['account.move.line']
            for row in matrix.iter_rows():
                if row.kpi.name == kpi_name:
                    for cell in row.iter_cells():
                        drilldown_arg = cell.drilldown_arg
                        res = mis.drilldown(drilldown_arg)
                        move_lines |= self.env['account.move.line'].search(res['domain'])
            return move_lines
        except Exception as e:
            _logger.warning(
                'MIS drilldown failed for KPI %s on PC %s: %s. '
                'Falling back to invoice-only data.',
                kpi_name, self.display_name, e,
            )
            return self.env['account.move.line']

    def calculate(self):
        for rec in self:
            if rec.state not in ['draft']:
                raise UserError(_("Du kan inte beräkna i denna status, ändra till utkast"))

            rec.line_ids.unlink()
            rec.invoice_ids = [(5,)]

            # --- Part 1: EU goods via MIS report (account 3106/3108) ---
            # This catches ALL entries on those accounts, including manual
            # journal entries that the old invoice-based approach missed.
            goods_move_lines = rec._get_move_lines_for_kpi('ForsVaruAnnatEg')

            # --- Part 2: EU services & goods via invoice iteration ---
            # Services (FTEU) and triangulation (3FEU) use 0% marker taxes.
            # The MIS KPI for these looks at tax_line_id, but 0% taxes
            # produce 0-amount tax lines so drilldown is unreliable.
            # We keep invoice-line approach for these.
            #
            # VTEU goods: also iterated here, but only for invoices NOT
            # already captured by MIS (on 3106/3108). The MIS drilldown on
            # ForsVaruAnnatEg (crd[3106,3108]) captures entries on those
            # accounts, but VTEU on other accounts (e.g. 3001) needs the
            # invoice iteration to be found.
            invoices = rec._get_period_invoices()

            # Build a dict: partner_id -> { goods, services, triangulation }
            partner_amounts = {}

            # Track which moves contributed via MIS (to avoid double-count)
            mis_move_ids = set()

            # Process goods move lines from MIS drilldown
            goods_moves = self.env['account.move']
            for line in goods_move_lines:
                pid = line.partner_id.id
                if not pid:
                    continue
                if pid not in partner_amounts:
                    partner_amounts[pid] = {
                        'goods': 0.0,
                        'services': 0.0,
                        'triangulation': 0.0,
                        'partner': line.partner_id,
                    }
                # credit - debit gives net revenue (credit positive for revenue accounts)
                partner_amounts[pid]['goods'] += line.credit - line.debit
                goods_moves |= line.move_id
                mis_move_ids.add(line.move_id.id)

            # Process VTEU/FTEU/3FEU via invoice lines
            # VTEU goods on invoices already captured by MIS (3106/3108)
            # are SKIPPED here to avoid double-counting.
            contributing_moves = goods_moves
            for invoice in invoices:
                pc_services = 0.0
                pc_triangulation = 0.0
                pc_goods = 0.0

                for line in invoice.invoice_line_ids:
                    tax_names = line.tax_ids.mapped('name')
                    # Use credit - debit (= balance in company currency)
                    # NOT price_subtotal which is in document currency.
                    # The MIS report (crd[3106,3108]) also uses company
                    # currency, so this keeps them consistent.
                    line_amount = line.credit - line.debit
                    # VTEU: only add if this invoice wasn't caught by MIS
                    # (MIS catches 3106/3108 entries; VTEU on other accounts
                    # needs invoice iteration to be found)
                    if 'VTEU' in tax_names and invoice.id not in mis_move_ids:
                        pc_goods += line_amount
                    if '3FEU' in tax_names:
                        pc_triangulation += line_amount
                    if any(tn in self._EU_SERVICE_TAX_NAMES for tn in tax_names):
                        pc_services += line_amount

                total_inv = pc_goods + pc_services + pc_triangulation
                if total_inv == 0.0:
                    continue

                pid = invoice.partner_id.id
                if not pid:
                    continue
                if pid not in partner_amounts:
                    partner_amounts[pid] = {
                        'goods': 0.0,
                        'services': 0.0,
                        'triangulation': 0.0,
                        'partner': invoice.partner_id,
                    }
                partner_amounts[pid]['goods'] += pc_goods
                partner_amounts[pid]['services'] += pc_services
                partner_amounts[pid]['triangulation'] += pc_triangulation

                # Only link this invoice if it had EU-relevant lines
                contributing_moves |= invoice

            # Link only contributing moves to this PC
            # (not all invoices in the period — they may be domestic)
            for move in contributing_moves:
                move.periodic_compilation_id = rec.id

            # Create declaration lines per partner
            for pid, vals in partner_amounts.items():
                goods = vals['goods']
                services = vals['services']
                triangulation = vals['triangulation']
                total = goods + services + triangulation
                if total == 0.0:
                    continue
                rec.env['account.declaration.line'].create({
                    'periodic_compilation_id': rec.id,
                    'pc_supplied_goods': goods,
                    'pc_triangulation': triangulation,
                    'pc_services_supplied': services,
                    'partner_id': pid,
                })

            rec.state = 'confirmed'
            rec.generate_pc_file()

    def generate_pc_file(self):
        for rec in self:
            rec.pc_file = None
            period_str = fields.Date.from_string(rec.date_start).strftime('%y%m')

            root = etree.Element('eSKDUpload', Version="6.0")
            orgnr = etree.SubElement(root, 'OrgNr')
            orgnr.text = rec.company_id.company_registry or ''

            ps = etree.SubElement(root, 'PeriodiskSammanstallning')
            period = etree.SubElement(ps, 'Period')
            period.text = fields.Date.from_string(rec.date_start).strftime('%Y%m')

            for line in rec.line_ids:
                kopare = etree.SubElement(ps, 'Kopare')
                vat_el = etree.SubElement(kopare, 'VATNr')
                vat_el.text = line.partner_id.vat or ''

                if line.pc_supplied_goods:
                    goods = etree.SubElement(kopare, 'LevereradeVaror')
                    goods.text = str(int(round(line.pc_supplied_goods)))
                if line.pc_triangulation:
                    triang = etree.SubElement(kopare, 'Trepartshandel')
                    triang.text = str(int(round(line.pc_triangulation)))
                if line.pc_services_supplied:
                    services = etree.SubElement(kopare, 'TillhandahallnaTjanster')
                    services.text = str(int(round(line.pc_services_supplied)))

            xml_bytes = etree.tostring(root, pretty_print=True, encoding='ISO-8859-1')
            xml_str = xml_bytes.decode('ISO-8859-1')
            xml_str = xml_str.replace('?>',
                '?>\n<!DOCTYPE eSKDUpload PUBLIC "-//Skatteverket, Sweden//DTD Skatteverket eSKDUpload-DTD Version 6.0//SV" "https://www.skatteverket.se/download/18.3f4496fd14864cc5ac99cb1/1415022101213/eSKDUpload_6p0.dtd">')
            rec.pc_file = base64.b64encode(xml_str.encode('ISO-8859-1'))
            rec.pc_file_name = 'periodisk_sammanstallning_%s.xml' % period_str

    def do_draft(self):
        for rec in self:
            rec.env['account.move'].search([
                ('periodic_compilation_id', '=', rec.id)
            ]).write({'periodic_compilation_id': False})
            rec.line_ids.unlink()
            rec.pc_file = None
            rec.state = 'draft'

    def do_cancel(self):
        for rec in self:
            rec.env['account.move'].search([
                ('periodic_compilation_id', '=', rec.id)
            ]).write({'periodic_compilation_id': False})
            rec.line_ids.unlink()
            rec.state = 'canceled'

    # --- Skatteverket API ---

    def action_send_to_skv(self):
        """Submit periodic compilation (eSKD XML) to Skatteverket via API."""
        self.ensure_one()

        if not self.pc_file:
            self.generate_pc_file()
        if not self.pc_file:
            raise UserError(_(
                "Could not generate periodic compilation file. "
                "Please run 'Calculate' first."))

        partner = self._get_skv_partner()
        if not partner or not partner.enable_skatteverket_api:
            raise UserError(_(
                "No Skatteverket API partner configured. "
                "Enable 'Skatteverket API' on a partner record in Contacts."))

        access_token = self._get_skv_access_token(partner)

        pc_api_url = (self.company_id.skv_pc_api_url
                      or self._get_skv_settings()['api_url'])

        xml_bytes = base64.b64decode(self.pc_file)

        headers = {
            'Authorization': 'Bearer %s' % access_token,
            'Content-Type': 'application/xml; charset=ISO-8859-1',
            'Accept': 'application/json',
        }

        try:
            response = requests.post(
                pc_api_url,
                data=xml_bytes,
                headers=headers,
                timeout=30,
            )
            _logger.info("SKV PC API response: %s %s", response.status_code, response.text[:500])

            if response.status_code in (200, 201, 202):
                self.write({
                    'skv_api_status': 'accepted',
                    'skv_response': 'OK: %s' % response.text[:500],
                    'skv_submitted_date': fields.Datetime.now(),
                    'state': 'done',
                })
            elif response.status_code == 401:
                partner.write({'access_token': False})
                self.write({
                    'skv_api_status': 'error',
                    'skv_response': 'Authentication failed. Token may have expired. Please retry.',
                })
                raise UserError(_(
                    "Authentication failed. Token may have expired. "
                    "Please retry the submission."))
            else:
                self.write({
                    'skv_api_status': 'error',
                    'skv_response': 'HTTP %s: %s' % (response.status_code, response.text[:1000]),
                    'skv_submitted_date': fields.Datetime.now(),
                })
                raise UserError(_(
                    "Skatteverket API returned error %s:\n%s")
                    % (response.status_code, response.text[:500]))

        except requests.exceptions.RequestException as e:
            self.write({
                'skv_api_status': 'error',
                'skv_response': 'Connection error: %s' % str(e),
                'skv_submitted_date': fields.Datetime.now(),
            })
            raise UserError(_(
                "Could not connect to Skatteverket API:\n%s")
                % str(e))

    @api.model
    def _cron_create_periodic_compilation(self):
        """Cron job: create next monthly periodic compilation automatically."""
        last = self.search([], order='date_stop desc', limit=1)
        if last:
            date_start = fields.Date.from_string(last.date_stop) + timedelta(days=1)
        else:
            today = fields.Date.today()
            date_start = today.replace(day=1)

        date_stop = date_start + relativedelta(months=1, days=-1)

        existing = self.search([
            ('date_start', '>=', fields.Date.to_string(date_start)),
            ('date_stop', '<=', fields.Date.to_string(date_stop)),
        ], limit=1)
        if existing:
            return False

        deadline = self._calculate_pc_deadline(date_stop)

        self.create({
            'date_start': fields.Date.to_string(date_start),
            'date_stop': fields.Date.to_string(date_stop),
            'date': fields.Date.to_string(deadline),
        })
        return True

    def action_download_pc_file(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/pc_file/%s?download=true' % (
                self._name, self.id, self.pc_file_name),
            'target': 'self',
        }

    def action_open_calendar_event(self):
        self.ensure_one()
        if self.event_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'calendar.event',
                'res_id': self.event_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def show_invoices(self):
        action = self.env['ir.actions.act_window']._for_xml_id(
            'account.action_move_journal_line')
        action.update({
            'display_name': _('Fakturor'),
            'domain': [('periodic_compilation_id', '=', self.id)],
        })
        return action

    def show_invoice_lines(self):
        action = self.env['ir.actions.act_window']._for_xml_id(
            'l10n_se_tax_report.action_invoice_line')
        action.update({
            'display_name': _('Fakturarader'),
            'domain': [('move_id.periodic_compilation_id', '=', self.id)],
            'context': {
                'group_by': ['partner_id'],
            },
        })
        return action


class AccountMove(models.Model):
    _inherit = 'account.move'

    periodic_compilation_id = fields.Many2one(
        comodel_name='account.periodic.compilation')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    pc_vat = fields.Char(string='VAT', related='move_id.partner_id.vat')


class AccountDeclarationLine(models.Model):
    _inherit = 'account.declaration.line'

    periodic_compilation_id = fields.Many2one(
        comodel_name='account.periodic.compilation')
    partner_id = fields.Many2one(comodel_name='res.partner')
    pc_supplied_goods = fields.Float(
        string='Levererade varor',
        help='Value of supplies of goods')
    pc_triangulation = fields.Float(
        string='Triangulering',
        help='Value of a triangulation')
    pc_services_supplied = fields.Float(
        string='Tillhandahållna tjänster',
        help='Value of services supplied')
    pc_purchasers_vat = fields.Char(
        string='Skatt / VAT', related='partner_id.vat')
    pc_name = fields.Char(
        string='Name', related='partner_id.name')

    def show_invoice_lines(self):
        """Show invoice lines for this partner within the PC period.

        Finds contributing moves for this partner, then shows all
        account.move.line records from those moves. This is more
        reliable than filtering by partner_id on move lines directly,
        since move lines may not always carry the partner_id field."""
        action = self.env['ir.actions.act_window']._for_xml_id(
            'l10n_se_tax_report.action_invoice_line')
        # Find all moves for this partner linked to the PC
        moves = self.env['account.move'].search([
            ('periodic_compilation_id', '=', self.periodic_compilation_id.id),
            ('partner_id', '=', self.partner_id.id),
        ])
        action.update({
            'display_name': _('Verifikat - %s') % self.partner_id.name,
            'domain': [('move_id', 'in', moves.ids)],
            'context': {
                'group_by': ['partner_id'],
            },
        })
        return action


class MisReportInstance(models.Model):
    _inherit = 'mis.report.instance'

    account_periodic_compilation_id = fields.One2many(
        comodel_name='account.periodic.compilation',
        inverse_name='generated_mis_report_id',
        string='Periodic Compilation',
    )
