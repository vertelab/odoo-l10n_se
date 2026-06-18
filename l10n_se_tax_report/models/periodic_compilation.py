from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
import base64
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
    pc_file_name = fields.Char(string="File Name", default="periodisk_sammanstallning.txt")

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
            self.date = self.date_stop + timedelta(days=12)

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
            company = rec.company_id
            period = fields.Date.from_string(rec.date_start)
            period_code = period.strftime('%y%m')

            contact = company.ag_contact[:1] if company.ag_contact else rec.env.user

            lines = [
                'SKV574008;',
                '%s;%s;%s;%s;%s' % (
                    company.company_registry or company.vat or '',
                    period_code,
                    (contact.name or rec.env.user.name)[:35],
                    contact.phone or '',
                    contact.email or '',
                ),
            ]

            for line in rec.line_ids:
                vat = line.partner_id.vat or ''
                goods = int(round(line.pc_supplied_goods))
                triang = int(round(line.pc_triangulation))
                services = int(round(line.pc_services_supplied))
                vals = []
                vals.append(vat or '')
                vals.append(str(goods) if goods else '')
                vals.append(str(triang) if triang else '')
                vals.append(str(services) if services else '')
                lines.append(';'.join(vals))

            content = '\n'.join(lines)
            rec.pc_file = base64.b64encode(content.encode('utf-8'))
            rec.pc_file_name = 'periodisk_sammanstallning_%s.txt' % period_code

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
