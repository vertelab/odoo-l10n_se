from odoo import models, fields, api, _
from odoo.exceptions import UserError

from dateutil.relativedelta import relativedelta


class AccountFiscalYear(models.Model):
    _inherit = "account.fiscalyear"

    vat_declaration_frequency = fields.Selection(
        selection=[('1', 'Month'), ('3', 'Quarter'), ('12', 'Year')],
        default='3', string='Skattedeklarationsfrekvens', help="Hur stor är momsdeklarationsperioden?"
    )
    moms_journal = fields.Many2one(comodel_name='account.journal', string='Momsdeklaration Journal')
    accounting_method = fields.Selection(
        selection=[('cash', 'Kontantmetoden'), ('invoice', 'Fakturametoden'), ],
        default='invoice', string='Redovisningsmetod',
        help="Ange redovisningsmetod, OBS även företag som tillämpar kontantmetoden skall välja fakturametoden "
             "i sista perioden/bokslutsperioden"
    )

    tax_declaration_ids = fields.One2many('account.vat.declaration', 'fiscalyear_id', string='Tax declarations')

    def _get_public_holidays(self, date):
        domain = [
            ('resource_id', '=', False),
            ('company_id', '=', self.company_id.id),
            ('date_from', '<=', date),
            ('date_to', '>=', date),
            ('calendar_id', '=', False),
        ]

        return self.env['resource.calendar.leaves'].search(domain, limit=1)

    def _get_next_business_day(self, date):
        current_date = date
        max_iterations = 10  # Prevent infinite loops
        iterations = 0

        while iterations < max_iterations:
            # Check if it's a weekend (Saturday=5, Sunday=6)
            if current_date.weekday() >= 5:
                current_date += relativedelta(days=1)
                iterations += 1
                continue

            # Check if it's a public holiday
            if self._get_public_holidays(current_date):
                current_date += relativedelta(days=1)
                iterations += 1
                continue

            # It's a business day
            return current_date
        return date

    def action_generate_tax_declaration(self):
        self.ensure_one()

        if not self.date_start or not self.date_stop:
            raise UserError(_("Fiscal year must have start and end dates."))

        frequency = int(self.vat_declaration_frequency)

        if frequency == 12:
            raise UserError(_("Yearly declarations must be created manually."))

        declaration_date_day = 26 if frequency == 1 else 12

        total_months = (self.date_stop.year - self.date_start.year) * 12 + \
                       (self.date_stop.month - self.date_start.month) + 1
        num_periods = total_months // frequency

        declarations = []
        current_start = self.date_start

        for period_num in range(num_periods):
            period_end = current_start + relativedelta(months=frequency, days=-1)

            if period_end > self.date_stop:
                period_end = self.date_stop

            declaration_date = period_end + relativedelta(months=1, day=declaration_date_day)

            declaration_date = self._get_next_business_day(declaration_date)

            declaration_data = {
                'name': f'Tax Declaration - {declaration_date.strftime('%B, %Y')}',
                'date_start': current_start,
                'date_stop': period_end,
                'date': declaration_date,
                'fiscalyear_id': self.id,
                'accounting_method': self.accounting_method,
            }

            declarations.append(declaration_data)

            current_start = period_end + relativedelta(days=1)

        TaxDeclaration = self.env['account.vat.declaration']
        created_declarations = TaxDeclaration.create(declarations)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Tax Declarations'),
            'res_model': 'account.vat.declaration',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_declarations.ids)],
            'context': {'create': False},
        }