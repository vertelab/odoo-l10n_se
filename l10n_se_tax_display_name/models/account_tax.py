from odoo import api, fields, models
from odoo.tools import html2plaintext, is_html_empty


class AccountTax(models.Model):
    _inherit = 'account.tax'
    _rec_name = 'display_name'

    display_name = fields.Char(
        compute='_compute_display_name',
        store=True,
    )

    def _get_display_label(self):
        self.ensure_one()
        if not is_html_empty(self.description):
            return html2plaintext(self.description).strip()
        return self.name

    @api.depends('name', 'description', 'type_tax_use', 'tax_scope', 'country_id', 'company_id')
    @api.depends_context('append_fields', 'append_type_to_tax_name')
    def _compute_display_name(self):
        type_tax_use = dict(self._fields['type_tax_use']._description_selection(self.env))
        fields_to_include = set(self.env.context.get('append_fields') or [])
        for record in self:
            name = record._get_display_label()
            if name:
                if self._context.get('append_type_to_tax_name'):
                    name += ' (%s)' % type_tax_use.get(record.type_tax_use)
                if 'company_id' in fields_to_include and len(self.env.companies) > 1:
                    name += ' (%s)' % record.company_id.display_name
                if record.country_id != record.company_id._accessible_branches()[:1].account_fiscal_country_id:
                    name += ' (%s)' % record.country_code
            record.display_name = name