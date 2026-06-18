from odoo import models, fields, api, _
from odoo.exceptions import UserError

from dateutil.relativedelta import relativedelta


class AccountFiscalYear(models.Model):
    _inherit = "account.fiscalyear"

    def action_generate_tax_declaration(self):
        self.ensure_one()

        if not self.date_start or not self.date_stop:
            raise UserError(_("Fiscal year must have start and end dates."))

        freq_str = self.company_id.vat_declaration_frequency
        if not freq_str:
            raise UserError(_(
                "VAT declaration frequency is not configured. "
                "Set it in Accounting → Configuration → Settings."))
        freq_map = {'month': 1, 'quarter': 3, 'year': 12}
        frequency = freq_map.get(freq_str, 3)

        if frequency == 1:
            declaration_date_day = 26
        else:
            declaration_date_day = 12

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

            is_yearend = period_end >= self.date_stop

            if not self.company_id.accounting_method:
                raise UserError(_(
                    "Accounting method is not configured for company %s. "
                    "Set it in Accounting → Configuration → Settings.")
                    % self.company_id.name)
            accounting_method = self.company_id.accounting_method
            declaration_data = {
                'name': f'{current_start}-{period_end}',
                'date_start': current_start,
                'date_stop': period_end,
                'date': declaration_date,
                'accounting_method': accounting_method,
                'accounting_yearend': is_yearend,
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