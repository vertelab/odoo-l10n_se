from odoo import api, fields, models, _
from datetime import date
import logging
_logger = logging.getLogger(__name__)


class PeriodicCompilationDemo(models.AbstractModel):
    _name = 'l10n_se_tax_report.periodic_compilation_demo'
    _description = 'Periodic Compilation Demo Generator'

    @api.model
    def generate_demo_data(self):
        """Generate demo data for periodic compilation:
        - EU partners with VAT numbers
        - Tax records for VTEU, FTEU, 3FEU, E
        - Products with EU taxes
        - Outgoing invoices to EU customers
        - Pre-calculated periodic compilation
        """
        if self.env['account.periodic.compilation'].search_count([]) > 0:
            _logger.info('Periodic compilation demo data already exists, skipping.')
            return True

        Tax = self.env['account.tax']
        Product = self.env['product.product']
        Partner = self.env['res.partner']
        Move = self.env['account.move']
        PC = self.env['account.periodic.compilation']

        # --- Find or create tax account ---
        tax_account = self.env['account.account'].search([
            ('code', '=', '2610'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if not tax_account:
            tax_account = self.env['account.account'].search([
                ('account_type', '=', 'liability_current'),
                ('company_id', '=', self.env.company.id),
            ], limit=1)

        # --- Find sale journal ---
        sale_journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if not sale_journal:
            _logger.warning('No sale journal found, skipping periodic compilation demo.')
            return False

        # --- Create EU tax records ---
        tax_defs = [
            ('tax_vteu_demo', 'VTEU', 'sale', 0.0, u'Försäljning varor till annat EU-land'),
            ('tax_fteu_demo', 'FTEU', 'sale', 0.0, u'Försäljning tjänster till annat EU-land'),
            ('tax_3feu_demo', '3FEU', 'sale', 0.0, u'Mellanmans försäljning trepartshandel'),
            ('tax_e_demo', 'E', 'sale', 0.0, u'Försäljning utanför EU'),
        ]

        taxes = {}
        for xmlid, name, tax_type, amount, desc in tax_defs:
            tax = Tax.search([('name', '=', name), ('company_id', '=', self.env.company.id)], limit=1)
            if not tax:
                tax = Tax.create({
                    'name': name,
                    'amount': amount,
                    'amount_type': 'percent',
                    'type_tax_use': tax_type,
                    'description': desc,
                    'price_include': False,
                    'invoice_repartition_line_ids': [
                        (0, 0, {
                            'repartition_type': 'base',
                            'factor_percent': 100,
                        }),
                        (0, 0, {
                            'repartition_type': 'tax',
                            'factor_percent': 100,
                            'account_id': tax_account.id,
                        }),
                    ],
                    'refund_repartition_line_ids': [
                        (0, 0, {
                            'repartition_type': 'base',
                            'factor_percent': 100,
                        }),
                        (0, 0, {
                            'repartition_type': 'tax',
                            'factor_percent': 100,
                            'account_id': tax_account.id,
                        }),
                    ],
                })
            taxes[name] = tax

        # --- Create EU partners with VAT numbers ---
        eu_partners = {}
        partner_defs = [
            ('partner_eu_france_demo', 'Camptocamp France SAS', 'base.fr', 'FR12345678901'),
            ('partner_eu_germany_demo', 'Handel GmbH', 'base.de', 'DE123456788'),
            ('partner_eu_netherlands_demo', 'Dutch Trading BV', 'base.nl', 'NL852341256B01'),
            ('partner_eu_denmark_demo', 'Nordic Supply ApS', 'base.dk', 'DK12345678'),
        ]

        for xmlid, name, country_ref, vat in partner_defs:
            partner = Partner.search([('vat', '=', vat)], limit=1)
            if not partner:
                partner = Partner.create({
                    'name': name,
                    'is_company': True,
                    'country_id': self.env.ref(country_ref).id,
                    'vat': vat,
                })
            eu_partners[name] = partner

        # --- Create products with EU taxes ---
        income_account = self.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        products = {}
        product_defs = [
            ('prod_eu_goods_demo', 'EU Goods (25%)', [taxes['VTEU'].id]),
            ('prod_eu_services_demo', 'EU Consulting Services', [taxes['FTEU'].id]),
            ('prod_eu_triangulation_demo', 'EU Triangulation Product', [taxes['3FEU'].id]),
            ('prod_export_demo', 'Export Product (non-EU)', [taxes['E'].id]),
        ]

        for xmlid, name, tax_ids in product_defs:
            product = Product.search([('name', '=', name)], limit=1)
            if not product:
                product = Product.create({
                    'name': name,
                    'type': 'consu',
                    'taxes_id': [(6, 0, tax_ids)],
                    'property_account_income_id': income_account.id,
                })
            products[name] = product

        # --- Create outgoing invoices to EU customers ---
        demo_year = date.today().year
        demo_month = max(1, date.today().month - 2)  # Two months ago for realistic demo

        invoice_date = date(demo_year, demo_month, 15)
        date_start = date(demo_year, demo_month, 1)
        date_stop = date(demo_year, demo_month + 1, 1) - date.resolution
        if demo_month == 11:
            date_stop = date(demo_year, 12, 31)
        elif demo_month >= 12:
            date_stop = date(demo_year, 12, 31)

        invoice_defs = [
            # France: VTEU goods
            ('invoice_eu_france_goods', eu_partners['Camptocamp France SAS'],
             products['EU Goods (25%)'], 10, 1500.0, [taxes['VTEU'].id]),
            ('invoice_eu_france_services', eu_partners['Camptocamp France SAS'],
             products['EU Consulting Services'], 5, 2000.0, [taxes['FTEU'].id]),
            # Germany: VTEU goods
            ('invoice_eu_germany_goods', eu_partners['Handel GmbH'],
             products['EU Goods (25%)'], 20, 1000.0, [taxes['VTEU'].id]),
            # Netherlands: 3FEU triangulation
            ('invoice_eu_nl_triang', eu_partners['Dutch Trading BV'],
             products['EU Triangulation Product'], 3, 5000.0, [taxes['3FEU'].id]),
            ('invoice_eu_nl_goods', eu_partners['Dutch Trading BV'],
             products['EU Goods (25%)'], 8, 750.0, [taxes['VTEU'].id]),
            # Denmark: FTEU services
            ('invoice_eu_dk_services', eu_partners['Nordic Supply ApS'],
             products['EU Consulting Services'], 2, 4500.0, [taxes['FTEU'].id]),
        ]

        for xmlid, partner, product, qty, price, tax_ids in invoice_defs:
            invoice = Move.create({
                'move_type': 'out_invoice',
                'partner_id': partner.id,
                'journal_id': sale_journal.id,
                'invoice_date': invoice_date,
                'invoice_line_ids': [
                    (0, 0, {
                        'product_id': product.id,
                        'quantity': qty,
                        'price_unit': price,
                        'name': product.name,
                        'tax_ids': [(6, 0, tax_ids)],
                    }),
                ],
            })
            if invoice.state == 'draft':
                invoice.action_post()

        # --- Create periodic compilation for the month ---
        deadline = self.env['account.declaration']._calculate_vat_deadline(date_stop, 1)

        pc = PC.create({
            'name': 'Periodisk sammanställning %s - %s' % (date_start, date_stop),
            'date_start': date_start,
            'date_stop': date_stop,
            'date': deadline,
            'target_move': 'posted',
        })

        if pc:
            pc.calculate()
            _logger.info(
                'Demo periodic compilation created: %s with %d lines',
                pc.name, len(pc.line_ids))

        return True


class account_invoice(models.Model):
    _inherit = 'account.move'
    
    @api.model
    def demo_add_tax_lines(self):
        record = self.env.ref(invoice_ref_id)
        record._onchange_invoice_line_ids()
        
        
class ir_config_parameter(models.Model):
    _inherit = 'ir.config_parameter'
    
    @api.model
    def set_value_to_ir_config_parameter(self, ir_config_parameter_ref_id):
        record = self.env.ref(ir_config_parameter_ref_id)
        record.value = self.env.ref('l10n_se_tax_report.moms_journal').id

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    @api.model
    def set_property_account_position_id(self, res_partner_ref_id, region_ref):
        res_partner_record = self.env.ref(res_partner_ref_id)
        region_record = self.env.ref(region_ref)
        # ~ This if case seems pointless but im just doing what the old account_invoice.yml file did.
        if  res_partner_record.property_account_position_id !=  region_record:
            res_partner_record.property_account_position_id = region_record
