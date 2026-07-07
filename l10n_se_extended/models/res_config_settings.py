# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ==================================================================
    # 1. Financial Reports
    # ==================================================================
    module_account_financial_report = fields.Boolean(
        string='OCA Financial Reports',
        help='General Ledger, Trial Balance, Aged Partner Balance, Journal Ledger, Open Items, VAT Report. '
             'Installs OCA account_financial_report.',
    )
    module_l10n_se_account_financial_report = fields.Boolean(
        string='Swedish Report Templates',
        help='Swedish-styled Balance Sheet and Income Statement. Installs l10n_se_account_financial_report.',
    )
    module_l10n_se_mis = fields.Boolean(
        string='MIS Builder (K2/K3)',
        help='Pre-built MIS templates for K2, K3, and municipality reports. Installs l10n_se_mis + K2/K3 variants.',
    )
    module_mis_builder_cash_flow = fields.Boolean(
        string='Cash Flow Statement',
        help='Cash flow statement for MIS Builder. Installs OCA mis_builder_cash_flow.',
    )

    # ==================================================================
    # 2. Bank & Payments
    # ==================================================================
    module_account_payment_order = fields.Boolean(
        string='Payment Orders (Bankgiro/Plusgiro/SEPA)',
        help='Create payment orders for SEPA, Bankgiro and Plusgiro. '
             'Installs OCA account_payment_order + l10n_se_account_payment_order + l10n_se_credit_transfer.',
    )
    module_account_payment_order_sepa_seb = fields.Boolean(
        string='SEB SEPA Fix',
        help='SEB-specific SEPA payment format. Installs account_payment_order_sepa_seb.',
    )
    module_account_payment_order_autogiro = fields.Boolean(
        string='Autogiro (Direct Debit)',
        help='Swedish Autogiro direct debit. Installs account_payment_order_autogiro.',
    )
    module_account_enablebanking = fields.Boolean(
        string='Auto Bank Sync (PSD2)',
        help='Automatic bank sync via Enable Banking API (Swedbank, SEB, Nordea, Handelsbanken). '
             'Installs account_enablebanking.',
    )
    module_l10n_se_mynt = fields.Boolean(
        string='Mynt Corporate Cards',
        help='Integration with Mynt corporate cards. Installs l10n_se_mynt.',
    )
    module_account_fortnox = fields.Boolean(
        string='Fortnox Integration',
        help='Data migration and sync with Fortnox. Installs account_fortnox.',
    )

    # ==================================================================
    # 3. Bank Import
    # ==================================================================
    module_l10n_se_account_bank_statement_import = fields.Boolean(
        string='Swedish Bank Statement Import',
        help='Import bank statements in Swedish formats (Bankgiro, BGMax). '
             'Installs l10n_se_account_bank_statement_import.',
    )
    module_l10n_se_ocr_reconcile = fields.Boolean(
        string='OCR Reconciliation',
        help='Automatic OCR-based reconciliation for Swedish payment references. '
             'Installs l10n_se_ocr_reconcile.',
    )

    # ==================================================================
    # 4. Supplier Invoices
    # ==================================================================
    # module_account_invoice_ai — kept for backward compatibility
    module_account_invoice_ai = fields.Boolean(
        string='AI Invoice Processing',
        help='Digitize your PDF or scanned documents using AI. '
             'Installs the account_invoice_ai module for automatic '
             'invoice processing with artificial intelligence.',
    )
    module_account_invoice_ai_3way_match = fields.Boolean(
        string='AI 3-Way Match',
        help='AI-powered PO/receipt/invoice matching. Requires AI Invoice Processing. '
             'Installs account_invoice_ai_3way_match.',
    )
    module_account_3way_match_ce = fields.Boolean(
        string='Manual 3-Way Match',
        help='Manual purchase order / receipt / invoice matching. Installs account_3way_match_ce.',
    )
    module_account_import_excel = fields.Boolean(
        string='Excel Invoice Import',
        help='Mass import invoices from Excel. Installs account_import_excel.',
    )

    # ==================================================================
    # 5. Customer Invoices
    # ==================================================================
    module_account_due_reminder = fields.Boolean(
        string='Payment Reminders',
        help='Automated payment reminders for overdue invoices. Installs account_due_reminder.',
    )
    module_account_mass_invoice_generation = fields.Boolean(
        string='Mass Invoice Generation',
        help='Generate invoices in bulk. Installs account_mass_invoice_generation.',
    )
    module_account_bulk_invoices = fields.Boolean(
        string='Bulk Invoice Operations',
        help='Bulk operations (print, send, validate). Installs account_bulk_invoices.',
    )

    # ==================================================================
    # 6. Tax & Authorities
    # ==================================================================
    module_l10n_se_tax_report = fields.Boolean(
        string='Tax Reports & SKV API',
        default=True,
        help='VAT, AGD, periodic summary via Skatteverket API. Installs l10n_se_tax_report.',
    )
    module_l10n_se_tax_account = fields.Boolean(
        string='Tax Account Reconciliation',
        default=True,
        help='Two-column tax account reconciliation vs Skatteverket API. Installs l10n_se_tax_account.',
    )
    module_l10n_se_agi = fields.Boolean(
        string='AGI (Individual Reporting)',
        help='Monthly AGI to Skatteverket via API. Installs l10n_se_agi.',
    )
    module_l10n_se_intrastat_product = fields.Boolean(
        string='Intrastat (SCB)',
        help='Intrastat reporting to SCB. Installs l10n_se_intrastat_product.',
    )
    module_l10n_se_tax_report_payment_order = fields.Boolean(
        string='Tax Payment Orders',
        help='Payment orders for tax payments. Installs l10n_se_tax_report_payment_order.',
    )

    # ==================================================================
    # 7. Period & Closing
    # ==================================================================
    module_account_period_vrtl = fields.Boolean(
        string='Swedish Periods',
        help='Swedish fiscal periods (monthly/quarterly) with closing controls. Installs account_period_vrtl.',
    )
    module_account_closed = fields.Boolean(
        string='Period Lock',
        help='Lock periods to prevent changes after closing. Installs account_closed.',
    )
    module_account_auto_reverse_vrtl = fields.Boolean(
        string='Auto-Reverse Entries',
        help='Automatically reverse journal entries next period. Installs account_auto_reverse_vrtl.',
    )
    module_account_deferred_revenue_expenses = fields.Boolean(
        string='Deferred Revenue & Expenses',
        help='Automatic revenue/expense accruals. Installs account_deferred_revenue_expenses.',
    )
    module_account_inter_company_rules_ce = fields.Boolean(
        string='Inter-Company Rules',
        help='Automatic inter-company transactions. Installs account_inter_company_rules_ce.',
    )

    # ==================================================================
    # 8. Year-End Closing
    # ==================================================================
    module_l10n_se_bokslut = fields.Boolean(
        string='Year-End Closing',
        help='Closing checklist, tax calculation, adjustments, annual report. Installs l10n_se_bokslut.',
    )

    # ==================================================================
    # 9. Budget & Forecast
    # ==================================================================
    module_account_mis_budget = fields.Boolean(
        string='Budget Management',
        help='MIS-based budgets with budget vs actual. Installs account_mis_budget.',
    )
    module_account_mis_budget_forecast = fields.Boolean(
        string='Dynamic Forecast',
        help='Dynamic forecast replacing budget with actuals for past periods. Installs account_mis_budget_forecast.',
    )
    module_account_budget_analytic_account = fields.Boolean(
        string='Budget per Analytic Account',
        help='Budgets per project/department. Installs account_budget_analytic_account.',
    )

    # ==================================================================
    # 10. Assets
    # ==================================================================
    module_account_asset_change = fields.Boolean(
        string='Asset Management',
        help='Extended asset management with change tracking. Installs account_asset_change + OCA asset management.',
    )
    module_account_asset_lot_stock = fields.Boolean(
        string='Asset Lot/Serial Tracking',
        help='Track assets by lot/serial number. Installs account_asset_lot_stock.',
    )
    module_account_asset_management_grant = fields.Boolean(
        string='Asset Grants',
        help='Grants and subsidies for assets. Installs account_asset_management_grant.',
    )
    module_account_loan_template = fields.Boolean(
        string='Loan Management',
        help='Loan templates and accounting. Installs account_loan_template.',
    )

    # ==================================================================
    # 11. SIE & Migration
    # ==================================================================
    module_l10n_se_sie = fields.Boolean(
        string='SIE Import/Export (Full)',
        help='Full SIE4 import/export with dimensions. Installs l10n_se_sie.',
    )
    module_l10n_se_sie_minimal = fields.Boolean(
        string='SIE Import (Minimal)',
        help='Lightweight SIE import for accounts and balances. Installs l10n_se_sie_minimal.',
    )

    # ==================================================================
    # 12. Document Management
    # ==================================================================
    module_account_attachment_directory = fields.Boolean(
        string='Document Directory',
        help='Organize documents in structured directories. Installs account_attachment_directory.',
    )
    module_account_move_directory = fields.Boolean(
        string='Journal Entry Directory',
        help='Organize journal entry attachments. Installs account_move_directory.',
    )

    # ==================================================================
    # Dependency Hints (onchange)
    # ==================================================================
    @api.onchange('module_account_invoice_ai_3way_match')
    def _onchange_ai_3way_match(self):
        if self.module_account_invoice_ai_3way_match:
            self.module_account_invoice_ai = True

    @api.onchange('module_account_mis_budget_forecast')
    def _onchange_mis_budget_forecast(self):
        if self.module_account_mis_budget_forecast:
            self.module_account_mis_budget = True

    @api.onchange('module_account_asset_lot_stock')
    def _onchange_asset_lot_stock(self):
        if self.module_account_asset_lot_stock:
            self.module_account_asset_change = True

    @api.onchange('module_account_asset_management_grant')
    def _onchange_asset_management_grant(self):
        if self.module_account_asset_management_grant:
            self.module_account_asset_change = True
