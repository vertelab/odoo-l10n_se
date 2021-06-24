from openerp import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class AccountVatDecorationMisTemplate(models.Model):
    _inherit = 'account.vat.declaration'
    momsdeklaration_template = fields.Many2one(comodel_name='mis.report', string='Mis_Templates')
    generated_mis_rapport = fields.Many2one(comodel_name='mis.report.instance', string='Mis_instance')
    
    @api.onchange("momsdeklaration_template")
    def _create_report_instance(self):
        if not self.momsdeklaration_template:
            return
        _logger.warning("jakmar _create_report_instance functionen, please go cool")
        _logger.warning('jakmar template id {}'.format(self.momsdeklaration_template.id))
        
        
        # ~ self.generated_mis_rapport = self.env['mis.report.instance'].create
        # ~ ([{
            # ~ 'company_id':1,
            # ~ 'report_id':self.momsdeklaration_template.id,
            # ~ 'comparison_mode':True,
            # ~ 'name':'deklaration_instance',
            # ~ 'target_move':'posted'
         # ~ }])
        
        
        # ~ <field name="name">Demo Expenses vs Budget</field>
        # ~ <field name="report_id" ref="mis_report_expenses" />
        # ~ <field name="comparison_mode" eval="True" />
        
          # ~ generated_mis_rapport = self.env['mis.record.instance'].create(
        # ~ {
            # ~ 'company_id':1,
            # ~ 'temporary':False,
            # ~ 'name':'momsdeklarations_mis_report',
            # ~ 'date_from': '2021-01-01',
            # ~ 'date_to': '2021-01-01',
            # ~ 'report_id':momsdeklaration_template[id]
            # ~ 'period_id':''
        # ~ }})
        
        # ~ <field name="name">Demo Expenses vs Budget</field>
        # ~ <field name="report_id" ref="mis_report_expenses" />
        # ~ <field name="comparison_mode" eval="True" />
        
        # ~ generated_mis_instance_period = self.env['mis.record.instance.period'].create(
        # ~ {
            # ~ 'company_id':1,
            # ~ 'mode':'fix'
            # ~ 'source':'actuals'
            # ~ 'name':'momsdeklarations_mis_report_instance_period',
            # ~ 'report_instance_id':'' 
        # ~ }})
    

        
        # ~ The onchange function runs when first creating a momsdekaration. At which time momsdeklaration_template is not set to anything which is why i have this if case
        # ~ if not self.momsdeklaration_template:
            # ~ return
        
        # ~ Step1: Create a data_period_type step, should be created in one of the data files since this only needs to be created once. 
        # ~ date_range_type_record = self.env['date.range.type'].create({'name':'Momsdeklaration tidsperiod type'}) 
        # ~ date_range_type_record = self.env['date.range.type'].search([('name','=','Momsdeklaration tidsperiod type')]) 
        # ~ _logger.warning("jakmar", date_range_type_record)
        # ~ _logger.warning("jakmar" + date_range_type_record.name)
        
        # ~ Step2: Using data_period_type create a data.range. Should in the future use the dates used in the form
        # ~ date_range_id_record  = self.env['date.range'].create(
        # ~ {'name':"Momsdeklaration tidsperiod",
        # ~ 'data_start':'2021-01-01',
        # ~ 'data_end':'2021-12-01',
        # ~ 'type_id':date_range_type_record.id
        # ~ })
        
        # ~ date_range_id_record  = self.env['date.range'].create({'product_id':self.id, 'date':self.status_date, 'status':self.status})
        # ~ date_range_id_record  = self.env['date.range'].create({'product_id':self.id, 'date':self.status_date, 'status':self.status})
        # ~ _logger.warning(self.momsdeklaration_template) 
        
         # ~ self.env['mis.report.instance'].create(company_id{'company_id':})
        
        # ~ self.env.cr.commit()
        
        # ~ generated_mis_rapport
        # ~ company_id many2one res.company
        # ~ name
        # ~ report_id 	many2one mir.report
        # ~ target_move selection
    # ~ def _generate_report_from_mis_template(self):
        


# ~ class AccountVatDecorationMisTemplateInverseRelation(models.Model):
    # ~ _inherit = 'mis.report'
    # ~ account_vat_declaration = fields.One2many(comodel_name='account.vat.declaration', inverse_name="momsdeklaration_template", string='account_vat_declaration')
