import base64
import logging
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MISReportExportImport(models.TransientModel):
    _name = 'mis.report.export.import'
    _description = 'MIS Report Export/Import Wizard'

    report_ids = fields.Many2many('mis.report', string='MIS Reports')
    data_file = fields.Binary(string='Import File')
    filename = fields.Char(string='Filename')
    export_format = fields.Selection([
        ('xml', 'XML')
    ], string='Export Format', default='xml')

    def action_export(self):
        _logger.info("Starting MIS Report export for %s reports", len(self.report_ids))
        if not self.report_ids:
            raise UserError(_("Please select at least one MIS Report to export."))

        xml_content = self._generate_xml()

        # Create attachment and return download action
        attachment = self.env['ir.attachment'].create({
            'name': f'mis_reports_{fields.Date.today()}.xml',
            'type': 'binary',
            'datas': base64.b64encode(xml_content.encode('utf-8')),
            'mimetype': 'application/xml',
            'res_model': self._name,
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _get_export_config(self):
        """Returns a configuration of fields to export for each model."""
        return {
            'mis.report': [
                'name', 'description', 'style_id', 'move_lines_source',
                'query_ids', 'kpi_ids', 'subkpi_ids', 'subreport_ids'
            ],
            'mis.report.style': [
                'name', 'color_inherit', 'color', 'background_color_inherit', 'background_color',
                'font_style_inherit', 'font_style', 'font_weight_inherit', 'font_weight',
                'font_size_inherit', 'font_size', 'indent_level_inherit', 'indent_level',
                'prefix_inherit', 'prefix', 'suffix_inherit', 'suffix', 'dp_inherit', 'dp',
                'divider_inherit', 'divider', 'hide_empty_inherit', 'hide_empty',
                'hide_always_inherit', 'hide_always'
            ],
            'mis.report.kpi': [
                'name', 'description', 'multi', 'auto_expand_accounts',
                'auto_expand_accounts_style_id', 'style_id', 'style_expression',
                'type', 'compare_method', 'accumulation_method', 'sequence',
                'expression_ids'
            ],
            'mis.report.kpi.expression': [
                'name', 'sequence', 'subkpi_id'
            ],
            'mis.report.subkpi': [
                'name', 'description', 'sequence'
            ],
            'mis.report.query': [
                'name', 'model_id', 'field_ids', 'aggregate', 'date_field',
                'domain', 'company_field_id'
            ],
            'mis.report.subreport': [
                'name', 'subreport_id', 'sequence'
            ]
        }

    def _generate_xml(self):
        root = ET.Element('mis_report_export', version="1.0")

        # Add metadata
        ET.SubElement(root, 'export_date').text = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Track exported records to avoid duplicates and handle circular refs
        exported_records = {} # (model, id): xml_id
        data_exported = set() # (model, id) - records whose DATA has been written to XML
        
        styles_root = ET.SubElement(root, 'styles')
        reports_root = ET.SubElement(root, 'reports')

        export_config = self._get_export_config()

        # Pre-populate exported_records with External IDs for top-level reports
        for report in self.report_ids:
            ext_id = report.get_external_id().get(report.id)
            exported_records[('mis.report', report.id)] = ext_id or f"mis_report_{report.id}"

        for report in self.report_ids:
            self._export_record(reports_root, report, export_config, exported_records, styles_root, data_exported)

        # Format with proper indentation
        rough_string = ET.tostring(root, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="    ", encoding='utf-8').decode('utf-8')

        return pretty_xml

    def _export_record(self, parent_elem, record, config, exported_records, styles_root, data_exported):
        model_name = record._name
        rec_key = (model_name, record.id)
        
        # If we already exported the DATA for this record, don't create another <record> tag
        if rec_key in data_exported:
            return

        record_elem = ET.SubElement(parent_elem, 'record', model=model_name)
        data_exported.add(rec_key)
        
        # Add external ID or internal XML ID
        ext_id = record.get_external_id().get(record.id)
        if ext_id:
            record_elem.set('id', ext_id)
            exported_records[rec_key] = ext_id
        else:
            xml_id = exported_records.get(rec_key) or f"{model_name.replace('.', '_')}_{record.id}"
            record_elem.set('xml_id', xml_id)
            exported_records[rec_key] = xml_id

        fields_to_export = config.get(model_name, [])
        for field_name in fields_to_export:
            field = record._fields.get(field_name)
            if not field:
                continue
            
            val = record[field_name]
            if not val and field.type != 'boolean':
                continue

            field_elem = ET.SubElement(record_elem, 'field', name=field_name)
            
            if field.type in ('char', 'text', 'html', 'selection'):
                field_elem.text = str(val)
            elif field.type == 'boolean':
                field_elem.text = 'True' if val else 'False'
            elif field.type in ('integer', 'float'):
                field_elem.text = str(val)
            elif field.type == 'many2one':
                if field.comodel_name in config:
                    # It's one of our MIS models
                    target_key = (field.comodel_name, val.id)
                    
                    # If target data not yet exported, export it to the appropriate section
                    if target_key not in data_exported:
                        if field.comodel_name == 'mis.report.style':
                            self._export_record(styles_root, val, config, exported_records, styles_root, data_exported)
                        elif field.comodel_name == 'mis.report' and target_key not in exported_records:
                            # Reference to another report not selected for export
                             ext_id = val.get_external_id().get(val.id)
                             if ext_id:
                                 exported_records[target_key] = ext_id

                    target_id = exported_records.get(target_key)
                    if target_id:
                        if '.' in target_id: # likely a real external ID
                            field_elem.set('ref', target_id)
                        else:
                            field_elem.set('xml_ref', target_id)
                elif field.comodel_name == 'ir.model':
                    field_elem.text = val.model
                elif field.comodel_name == 'ir.model.fields':
                    field_elem.text = f"{val.model_id.model}.{val.name}"
                else:
                    ext_id = val.get_external_id().get(val.id)
                    if ext_id:
                        field_elem.set('ref', ext_id)
                    else:
                        if 'name' in val._fields:
                            field_elem.set('search', f"[('name', '=', '{val.name}')]")
                        else:
                            _logger.warning("Many2one field %s in %s has no external ID and no name field", field_name, model_name)

            elif field.type in ('one2many', 'many2many'):
                if field.type == 'many2many' and field.comodel_name == 'ir.model.fields':
                    for child_record in val:
                        child_elem = ET.SubElement(field_elem, 'value')
                        child_elem.text = f"{child_record.model_id.model}.{child_record.name}"
                else:
                    for child_record in val:
                        self._export_record(field_elem, child_record, config, exported_records, styles_root, data_exported)

    def action_import(self):
        if not self.data_file:
            raise UserError(_("Please select a file to import."))

        try:
            xml_content = base64.b64decode(self.data_file)
            root = ET.fromstring(xml_content)
            
            # Map of XML IDs to Odoo records
            id_map = {}

            # First pass: Styles
            styles_node = root.find('styles')
            if styles_node is not None:
                for style_node in styles_node.findall('record'):
                    self._import_record(style_node, id_map)

            # Second pass: Reports
            reports_node = root.find('reports')
            if reports_node is not None:
                for report_node in reports_node.findall('record'):
                    self._import_record(report_node, id_map)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Import Successful'),
                    'message': _('MIS Reports imported successfully!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error("Import failed: %s", str(e), exc_info=True)
            raise UserError(_("Import failed: %s") % str(e))

    def _import_record(self, record_node, id_map, parent_info=None):
        model_name = record_node.get('model')
        xml_id = record_node.get('id') or record_node.get('xml_id')
        
        data = {}
        if parent_info:
            data[parent_info[0]] = parent_info[1]

        relational_data = []

        for field_node in record_node.findall('field'):
            field_name = field_node.get('name')
            field = self.env[model_name]._fields.get(field_name)
            if not field:
                continue

            if field.type in ('one2many', 'many2many'):
                relational_data.append((field_name, field_node))
                continue

            ref = field_node.get('ref')
            xml_ref = field_node.get('xml_ref')
            search_domain = field_node.get('search')
            
            if ref:
                record = self.env.ref(ref, raise_if_not_found=False)
                if record:
                    data[field_name] = record.id
            elif xml_ref:
                if xml_ref in id_map:
                    data[field_name] = id_map[xml_ref].id
            elif search_domain:
                try:
                    import ast
                    domain = ast.literal_eval(search_domain)
                    found_record = self.env[field.comodel_name].search(domain, limit=1)
                    if found_record:
                        data[field_name] = found_record.id
                except:
                    pass
            elif field.type == 'many2one':
                if field.comodel_name == 'ir.model':
                    model = self.env['ir.model'].search([('model', '=', field_node.text)])
                    if model:
                        data[field_name] = model.id
                elif field.comodel_name == 'ir.model.fields':
                    if field_node.text and '.' in field_node.text:
                        m, f = field_node.text.split('.')
                        f_record = self.env['ir.model.fields'].search([('model', '=', m), ('name', '=', f)])
                        if f_record:
                            data[field_name] = f_record.id
            else:
                if field.type == 'boolean':
                    data[field_name] = field_node.text == 'True'
                elif field.type == 'integer':
                    data[field_name] = int(field_node.text) if field_node.text else 0
                elif field.type == 'float':
                    data[field_name] = float(field_node.text) if field_node.text else 0.0
                else:
                    data[field_name] = field_node.text

        # Create or update record
        record = None
        # Match by External ID
        if xml_id and not record_node.get('xml_id'):
            record = self.env.ref(xml_id, raise_if_not_found=False)
        
        # Match by Name + Parent if not found by ID (Prevents duplicates for KPIs, Queries, etc.)
        if not record:
            name = data.get('name')
            if name:
                domain = [('name', '=', name)]
                if parent_info and model_name != 'mis.report':
                    domain.append((parent_info[0], '=', parent_info[1]))
                record = self.env[model_name].search(domain, limit=1)
            
        if record:
            record.write(data)
        else:
            record = self.env[model_name].create(data)

        if xml_id:
            id_map[xml_id] = record

        # Process relational data
        for field_name, field_node in relational_data:
            field = record._fields.get(field_name)
            
            if field.type == 'many2many' and field.comodel_name == 'ir.model.fields':
                commands = []
                for val_node in field_node.findall('value'):
                    if val_node.text and '.' in val_node.text:
                        m, f = val_node.text.split('.')
                        f_record = self.env['ir.model.fields'].search([('model', '=', m), ('name', '=', f)])
                        if f_record:
                            commands.append((4, f_record.id))
                if commands:
                    record.write({field_name: commands})
            elif field.type == 'one2many':
                for child_node in field_node.findall('record'):
                    # Pass parent ID to satisfy 'required' parent relations
                    self._import_record(child_node, id_map, parent_info=(field.inverse_name, record.id))
            elif field.type == 'many2many':
                 commands = []
                 for child_node in field_node.findall('record'):
                     child_record = self._import_record(child_node, id_map)
                     commands.append((4, child_record.id))
                 if commands:
                     record.write({field_name: commands})

        return record
