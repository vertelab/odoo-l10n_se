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

    def _invoice_ids_count(self):
        for rec in self:
            rec.invoice_ids_count = len(rec.invoice_ids)
    invoice_ids_count = fields.Integer(compute='_invoice_ids_count')

    def _move_line_ids_count(self):
        for rec in self:
            rec.move_line_ids_count = len(rec.line_ids)
    move_line_ids_count = fields.Integer(compute='_move_line_ids_count')

    @api.onchange('date_start', 'date_stop')
    def _onchange_period_dates(self):
        if self.date_start and self.date_stop:
            self.name = '%s %s - %s' % (self._report_name, self.date_start, self.date_stop)
            self.date = self._calculate_vat_deadline(
                fields.Date.from_string(self.date_stop), 1)

    @api.model
    def create(self, vals):
        """Ensure date and name are computed when created from code (cron, batch)."""
        if vals.get('date_start') and vals.get('date_stop'):
            if not vals.get('date'):
                date_stop = fields.Date.from_string(vals['date_stop'])
                vals['date'] = fields.Date.to_string(
                    self._calculate_vat_deadline(date_stop, 1))
            if not vals.get('name'):
                vals['name'] = '%s %s - %s' % (
                    self._report_name, vals['date_start'], vals['date_stop'])
        return super(account_periodic_compilation, self).create(vals)

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

    def calculate(self):
        for rec in self:
            if rec.state not in ['draft']:
                raise UserError(_("Du kan inte beräkna i denna status, ändra till utkast"))

            rec.line_ids.unlink()
            rec.invoice_ids = [(5,)]

            partner_ids = []
            invoices = rec._get_period_invoices()

            for invoice in invoices:
                pc_supplied_goods = 0.0
                pc_triangulation = 0.0
                pc_services_supplied = 0.0

                for line in invoice.invoice_line_ids:
                    tax_names = line.tax_ids.mapped('name')
                    if 'VTEU' in tax_names:
                        pc_supplied_goods += line.price_subtotal
                    if '3FEU' in tax_names:
                        pc_triangulation += line.price_subtotal
                    if any(tn in self._EU_SERVICE_TAX_NAMES for tn in tax_names):
                        pc_services_supplied += line.price_subtotal

                total = pc_supplied_goods + pc_triangulation + pc_services_supplied
                if total == 0.0:
                    continue

                invoice.periodic_compilation_id = rec.id

                if invoice.partner_id.id in partner_ids:
                    existing = rec.line_ids.filtered(
                        lambda l: l.partner_id == invoice.partner_id)
                    if existing:
                        existing.pc_supplied_goods += pc_supplied_goods
                        existing.pc_triangulation += pc_triangulation
                        existing.pc_services_supplied += pc_services_supplied
                else:
                    rec.env['account.declaration.line'].create({
                        'periodic_compilation_id': rec.id,
                        'pc_supplied_goods': pc_supplied_goods,
                        'pc_triangulation': pc_triangulation,
                        'pc_services_supplied': pc_services_supplied,
                        'partner_id': invoice.partner_id.id,
                    })
                    partner_ids.append(invoice.partner_id.id)

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

        deadline = self._calculate_vat_deadline(date_stop, 1)

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
        action = self.env['ir.actions.act_window']._for_xml_id(
            'l10n_se_tax_report.action_invoice_line')
        action.update({
            'display_name': _('Verifikat'),
            'domain': [
                ('move_id', 'in',
                 self.periodic_compilation_id.invoice_ids.mapped('id')),
                ('partner_id', '=', self.partner_id.id),
            ],
        })
        return action
