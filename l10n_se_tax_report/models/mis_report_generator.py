from openerp import models, fields, api
import logging
import base64
from lxml import etree

_logger = logging.getLogger(__name__)

class AccountVatDecoration(models.Model):
    _inherit = 'account.vat.declaration'
    
    momsdeklaration_template = fields.Many2one(comodel_name='mis.report', string='Mis_Templates',required=True)
    # ~ Should be one2one. account.vat.declaration should have one unique mis.report.instance.
    generated_mis_report = fields.Many2one(comodel_name='mis.report.instance', string='Mis_instance', ondelete='cascade')
    eskd_file_mis = fields.Binary(string="eSKD-file_mis",readonly=True, compute='_compute_xml_file')
    
    @api.model
    def create(self,values):
        _logger.warning(values)
        momsdeklaration_name = values["name"]
        _logger.warning('jakmar start date: {}'.format(values["name"]))
        
        start_date = self.env['account.period'].browse(values["period_start"]).date_start
        # ~ _logger.warning('jakmar start date: {}'.format(start_date))
        
        stop_date = self.env['account.period'].browse(values["period_stop"]).date_stop
        # ~ _logger.warning('jakmar stop date: {}'.format(stop_date))
        
        mis_template_id = self.env['account.period'].browse(values["momsdeklaration_template"]).id
        # ~ _logger.warning('jakmar generated_mis_report id {}'.format(mis_template_id))
        
        # ~ _logger.warning('jakmar company id: {}'.format(self.env.ref("base.main_company").id))
        
        record = super(AccountVatDecoration, self).create(values)
        report_instance = self.env["mis.report.instance"].create(
            dict(
                name= " mis genererad momsdeklaration report",
                report_id=mis_template_id,
                company_id=self.env.ref("base.main_company").id,
                period_ids=[
                    (
                        0,
                        0,
                        dict(
                            name="p3",
                            mode="fix",
                            manual_date_from=start_date,
                            manual_date_to=stop_date,
                        ),
                    )
                ],
            )
        )
        
        record.generated_mis_report = report_instance.id
        return record
     # ~ Update the file everytime it's viewed, should also happen when chaning templates
    @api.depends('generated_mis_report','eskd_file_mis')
    def _compute_xml_file(self):
        eskd_file_mis = None
        root = etree.Element('eSKDUpload', Version="6.0")
        orgnr = etree.SubElement(root, 'OrgNr')
        orgnr.text = self.env.user.company_id.company_registry or ''
        moms = etree.SubElement(root, 'Moms')
        period = etree.SubElement(moms, 'Period')
        period.text = self.period_stop.date_start[:4] + self.period_stop.date_start[5:7]
        
        matrix = self.generated_mis_report._compute_matrix()
        for row in matrix.iter_rows():
            vals = [c.val for c in row.iter_cells()]
            _logger.warning('jakmar Konto{} En rad: {}'.format(row.kpi.name,vals))
            if not vals[0] == '0':
                tax = etree.SubElement(moms, row.kpi.name)
                tax.text = str(vals[0])
        
        momsbetala = etree.SubElement(moms, 'MomsBetala')
        momsbetala.text = str(int(round(self.vat_momsbetala)))
        free_text = etree.SubElement(moms, 'TextUpplysningMoms')
        free_text.text = self.free_text or ''
        
        xml = etree.tostring(root,pretty_print=True, encoding="ISO-8859-1")
        xml = xml.replace('?>', '?>\n<!DOCTYPE eSKDUpload PUBLIC "-//Skatteverket, Sweden//DTD Skatteverket eSKDUpload-DTD Version 6.0//SV" "https://www.skatteverket.se/download/18.3f4496fd14864cc5ac99cb1/1415022101213/eSKDUpload_6p0.dtd">')
        self.eskd_file_mis = base64.b64encode(xml)
        
        
class MisReportInstance(models.Model):
    _inherit = 'mis.report.instance'
    # ~ Should be one2one. account.vat.declaration should have one unique mis.report.instance. This is to insure that the instance created also gets deleted when the account.vat.declaration does.
    account_vat_declaration_id = fields.One2many(comodel_name='account.vat.declaration', inverse_name ='generated_mis_report', string="account vat deckaration id", ondelete='cascade')
    


    # ~ period_id = fields.Many2one(
        # ~ comodel_name="mis.report.instance.period",
        # ~ string="Parent column",
        # ~ ondelete="cascade",
        # ~ required=True,
    # ~ )

        # ~ source_sumcol_ids = fields.One2many(
        # ~ comodel_name="mis.report.instance.period.sum",
        # ~ inverse_name="period_id",
        # ~ string="Columns to sum",
    # ~ )
