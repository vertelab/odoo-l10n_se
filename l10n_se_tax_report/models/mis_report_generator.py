from openerp import models, fields, api
import logging
import base64
from lxml import etree

_logger = logging.getLogger(__name__)

class account_vat_decoration(models.Model):
    _inherit = 'account.vat.declaration'
    momsdeklaration_template = fields.Many2one(comodel_name='mis.report', string='Mis_Templates')
    eskd_file_mis = fields.Binary(string="eSKD-file_mis",compute='_compute_xml_file')
    # ~ generated_mis_report_int = fields.Integer(compute='_compute_int_id')
    generated_mis_report_int = fields.Integer()
    generated_mis_report_id = fields.Many2one(comodel_name='mis.report.instance', string='mis_report_instance', default = lambda self: self._generate_mis_report(), ondelete='cascade')

    @api.model
    def _generate_mis_report(self):
        report_instance = self.env["mis.report.instance"].create(
            dict(
                name="mis genererad momsdeklaration report",
                report_id = self.env.ref('l10n_se_mis.report_md').id,
                company_id = self.env.ref("base.main_company").id,
                period_ids=[
                    (
                        0,
                        0,
                        dict(
                            name = "p1",
                            mode = "fix",
                            manual_date_from="2020-01-01",
                            manual_date_to="2020-12-31",
                        ),
                    )
                ],
            )
        )
        return report_instance
            
    @api.model
    def create(self,values):
        start_date = self.env['account.period'].browse(values["period_start"]).date_start
        stop_date = self.env['account.period'].browse(values["period_stop"]).date_stop
        
        # ~ mis_instance_record = self.env['mis.report.instance'].browse(values["generated_mis_report_id"])
        record = super(account_vat_decoration, self).create(values)
        record.generated_mis_report_id.period_ids.write({'manual_date_from':start_date})
        record.generated_mis_report_id.period_ids.write({'manual_date_to':stop_date})
        return record
        
    @api.multi
    def write(self, values):
        res = super(account_vat_decoration, self).write(values)
        mis_instance_record = self.env['mis.report.instance'].browse(self.generated_mis_report_id.id)
        if "period_start" in values:
            start_date = self.env['account.period'].browse(values["period_start"]).date_start
            mis_instance_record.period_ids.write({'manual_date_from':start_date})
        if "period_stop" in values:
            stop_date = self.env['account.period'].browse(values["period_stop"]).date_stop
            mis_instance_record.period_ids.write({'manual_date_to':stop_date})
        return res
    
    def _compute_xml_file(self):
        if type(self.period_start.date_start) == bool or type(self.period_stop.date_stop) == bool:
            return
        eskd_file_mis = None
        root = etree.Element('eSKDUpload', Version="6.0")
        orgnr = etree.SubElement(root, 'OrgNr')
        orgnr.text = self.env.user.company_id.company_registry or ''
        moms = etree.SubElement(root, 'Moms')
        period = etree.SubElement(moms, 'Period')
        period.text = self.period_stop.date_start[:4] + self.period_stop.date_start[5:7]
        matrix = self.generated_mis_report_id._compute_matrix()
        
        for row in matrix.iter_rows():
            _logger.warning('jakmar: row : {}'.format(row.kpi))
            _logger.warning('jakmar: row.matrix : {}'.format(row._matrix))
            _logger.warning('jakmar: row.matrix : {}'.format(row.account_id))
            # ~ for cell in row.iter_cells():
                # ~ _logger.warning('jakmar: cell : {}'.format(cell))
            vals = [c.val for c in row.iter_cells()]
            # If the vals[0] is zero it becomes a class 'odoo.addons.mis_builder.models.accounting_none.AccountingNoneType. Otherwise it's a float and should be added to the file
            if  type(vals[0]) == float and vals[0] > 0.0:
                tax = etree.SubElement(moms, row.kpi.name)
                # ~ Lambda is used to fix trailing zeros, like example
                formatNumber = lambda n: n if n%1 else int(n)
                tax.text = str(formatNumber(vals[0]))
        
        momsbetala = etree.SubElement(moms, 'MomsBetala')
        momsbetala.text = str(int(round(self.vat_momsbetala)))
        free_text = etree.SubElement(moms, 'TextUpplysningMoms')
        free_text.text = self.free_text or ''
        
        xml = etree.tostring(root,pretty_print=True, encoding="ISO-8859-1")
        xml = xml.replace('?>', '?>\n<!DOCTYPE eSKDUpload PUBLIC "-//Skatteverket, Sweden//DTD Skatteverket eSKDUpload-DTD Version 6.0//SV" "https://www.skatteverket.se/download/18.3f4496fd14864cc5ac99cb1/1415022101213/eSKDUpload_6p0.dtd">')
        self.eskd_file_mis = base64.b64encode(xml)
        
    @api.multi
    def  show_preview(self):
        self.ensure_one()
        return self.generated_mis_report_id.preview()
    

class mis_report_instance(models.Model):
    _inherit = 'mis.report.instance'
    # ~ Should be one2one. account.vat.declaration should have one unique mis.report.instance. This is to insure that the instance created also gets deleted when the account.vat.declaration does.
    account_vat_declaration_id = fields.One2many(comodel_name='account.vat.declaration', inverse_name ='generated_mis_report_id', string="account vat deckaration id")
    
    

