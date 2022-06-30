from odoo import api, fields, models, _, exceptions


import logging
_logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    _inherit = 'account.journal'
    
    is_card_journal = fields.Boolean()
    # ~ card_debit_account = fields.Many2one('account.account', string='Card Debit Account',
    # ~ domain="[('deprecated', '=', False), ('company_id', '=', company_id),"
               # ~ "'|', ('user_type_id', '=', default_account_type),"
               # ~ "('user_type_id.type', '=', 'payable')]")
    # ~ card_credit_account = fields.Many2one('account.account', string='Card Credit Account',
    # ~ domain="[('deprecated', '=', False), ('company_id', '=', company_id),"
               # ~ "'|', ('user_type_id', '=', default_account_type),"
               # ~ "('user_type_id.type', '=', 'receivable')]")
    card_debit_account = fields.Many2one('account.account', string='Card Debit Account')
    card_credit_account = fields.Many2one('account.account', string='Card Credit Account')
    
 


    def open_action_with_context_mynt(self):
        _logger.warning("{open_action_with_context_mynt}"*10)
        action_name = self.env.context.get('action_name', False)
        if not action_name:
            return False
        ctx = dict(self.env.context, default_journal_id=self.id)
        _logger.warning(f"before {ctx=}")
        if ctx.get('search_default_journal', False):
            ctx.update(search_default_journal_id=self.id)
            ctx['search_default_journal'] = False  # otherwise it will do a useless groupby in bank statements
        ctx.pop('group_by', None)
        _logger.warning(f"after {ctx=}")
        action = self.env['ir.actions.act_window']._for_xml_id(f"l10n_se_mynt.{action_name}")
        action['context'] = ctx
        if ctx.get('use_domain', False):
            action['domain'] = isinstance(ctx['use_domain'], list) and ctx['use_domain'] or ['|', ('journal_id', '=', self.id), ('journal_id', '=', False)]
            action['name'] = _(
                "%(action)s for journal %(journal)s",
                action=action["name"],
                journal=self.name,
            )
        return action
