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

    instance_ids = fields.Many2many('mis.report.instance', string='MIS Report Instances')
    data_file = fields.Binary(string='Import File')
    filename = fields.Char(string='Filename')
    export_format = fields.Selection([
        ('xml', 'XML')
    ], string='Export Format', default='xml')

    @api.model
    def default_get(self, fields_list):
        res = super(MISReportExportImport, self).default_get(fields_list)
        if self._context.get('active_model') == 'mis.report.instance' and self._context.get('active_ids'):
            res['instance_ids'] = [(6, 0, self._context.get('active_ids'))]
        return res

    def action_export(self):
        _logger.info("Starting MIS Report Instance export for %s instances", len(self.instance_ids))
        if not self.instance_ids:
            raise UserError(_("Please select at least one MIS Report Instance to export."))

        xml_content = self._generate_xml()

        # Create attachment and return download action
        attachment = self.env['ir.attachment'].create({
            'name': f'mis_report_instances_{fields.Date.today()}.xml',
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
            'mis.report.instance': [
                'name', 'description', 'report_id', 'target_move',
                'multi_company', 'landscape_pdf', 'no_auto_expand_accounts',
                'display_columns_description', 'date_from', 'date_to',
                'analytic_domain', 'widget_show_filters', 'widget_show_settings_button',
                'widget_show_pivot_date', 'period_ids'
            ],
            'mis.report.instance.period': [
                'name', 'sequence', 'mode', 'type', 'is_ytd', 'offset', 'duration',
                'manual_date_from', 'manual_date_to', 'normalize_factor', 'subkpi_ids',
                'source', 'source_aml_model_id', 'source_sumcol_ids', 'source_sumcol_accdet',
                'source_cmpcol_from_id', 'source_cmpcol_to_id', 'analytic_domain'
            ],
            'mis.report.instance.period.sum': [
                'period_to_sum_id', 'sign'
            ],
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
        
        # Track exported records
        exported_records = {} # (model, id): xml_id
        data_exported = set() # (model, id)
        
        styles_root = ET.SubElement(root, 'styles')
        templates_root = ET.SubElement(root, 'templates')
        instances_root = ET.SubElement(root, 'instances')

        export_config = self._get_export_config()

        for instance in self.instance_ids:
            self._export_record(instances_root, instance, export_config, exported_records, styles_root, templates_root, data_exported)

        # Format with proper indentation
        rough_string = ET.tostring(root, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="    ", encoding='utf-8').decode('utf-8')

        return pretty_xml

    def _export_record(self, parent_elem, record, config, exported_records, styles_root, templates_root, data_exported):
        model_name = record._name
        rec_key = (model_name, record.id)
        
        if rec_key in data_exported:
            return

        record_elem = ET.SubElement(parent_elem, 'record', model=model_name)
        data_exported.add(rec_key)
        
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
                    target_key = (field.comodel_name, val.id)
                    
                    if target_key not in data_exported:
                        if field.comodel_name == 'mis.report.style':
                            self._export_record(styles_root, val, config, exported_records, styles_root, templates_root, data_exported)
                        elif field.comodel_name == 'mis.report':
                            self._export_record(templates_root, val, config, exported_records, styles_root, templates_root, data_exported)
                    
                    target_id = exported_records.get(target_key)
                    if target_id:
                        if '.' in target_id:
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
                        if field.comodel_name == 'res.currency':
                             field_elem.set('search', f"[('name', '=', '{val.name}')]")
                        elif field.comodel_name == 'res.company':
                             field_elem.set('search', f"[('name', '=', '{val.name}')]")
                        elif 'name' in val._fields:
                            field_elem.set('search', f"[('name', '=', '{val.name}')]")

            elif field.type in ('one2many', 'many2many'):
                if field.type == 'many2many' and field.comodel_name == 'ir.model.fields':
                    for child_record in val:
                        child_elem = ET.SubElement(field_elem, 'value')
                        child_elem.text = f"{child_record.model_id.model}.{child_record.name}"
                elif field.type == 'many2many' and field.comodel_name in config:
                    for child_record in val:
                        target_key = (field.comodel_name, child_record.id)
                        target_id = exported_records.get(target_key)
                        if target_id:
                            child_node = ET.SubElement(field_elem, 'record_ref')
                            if '.' in target_id:
                                child_node.set('ref', target_id)
                            else:
                                child_node.set('xml_ref', target_id)
                else:
                    for child_record in val:
                        self._export_record(field_elem, child_record, config, exported_records, styles_root, templates_root, data_exported)

    def action_import(self):
        if not self.data_file:
            raise UserError(_("Please select a file to import."))

        try:
            xml_content = base64.b64decode(self.data_file)
            root = ET.fromstring(xml_content)
            
            # Map of XML IDs to Odoo records
            id_map = {}
            # List of (record, field_name, xml_ref) to resolve after all records are created
            postponed_refs = []

            # First pass: Styles
            styles_node = root.find('styles')
            if styles_node is not None:
                for node in styles_node.findall('record'):
                    self._import_record(node, id_map, postponed_refs=postponed_refs)

            # Second pass: Templates
            templates_node = root.find('templates')
            if templates_node is not None:
                for node in templates_node.findall('record'):
                    self._import_record(node, id_map, postponed_refs=postponed_refs)

            # Third pass: Instances
            instances_node = root.find('instances')
            if instances_node is not None:
                for node in instances_node.findall('record'):
                    self._import_record(node, id_map, postponed_refs=postponed_refs)

            # Final pass: Resolve postponed references
            for record, field_name, xml_ref in postponed_refs:
                if xml_ref in id_map:
                    record.write({field_name: id_map[xml_ref].id})
                else:
                    _logger.warning("Could not resolve postponed reference %s for field %s in %s", xml_ref, field_name, record._name)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Import Successful'),
                    'message': _('MIS Report Instances imported successfully!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error("Import failed: %s", str(e), exc_info=True)
            raise UserError(_("Import failed: %s") % str(e))

    def _import_record(self, record_node, id_map, parent_info=None, postponed_refs=None):
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
                elif postponed_refs is not None:
                    # Resolution will be postponed
                    pass
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
        if xml_id and not record_node.get('xml_id'):
            record = self.env.ref(xml_id, raise_if_not_found=False)
        
        if not record:
            name = data.get('name')
            if name:
                domain = [('name', '=', name)]
                if parent_info and model_name not in ('mis.report', 'mis.report.instance', 'mis.report.style'):
                    domain.append((parent_info[0], '=', parent_info[1]))
                record = self.env[model_name].search(domain, limit=1)
            
        if record:
            record.write(data)
        else:
            record = self.env[model_name].create(data)

        if xml_id:
            id_map[xml_id] = record

        # Register postponed references for this record
        if postponed_refs is not None:
            for field_node in record_node.findall('field'):
                xml_ref = field_node.get('xml_ref')
                if xml_ref and xml_ref not in id_map:
                    postponed_refs.append((record, field_node.get('name'), xml_ref))

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
            elif field.type == 'many2many' and field.comodel_name in self._get_export_config():
                commands = []
                for ref_node in field_node.findall('record_ref'):
                    target_id = None
                    if ref_node.get('ref'):
                        target = self.env.ref(ref_node.get('ref'), raise_if_not_found=False)
                        if target:
                            target_id = target.id
                    elif ref_node.get('xml_ref'):
                        if ref_node.get('xml_ref') in id_map:
                            target_id = id_map[ref_node.get('xml_ref')].id
                    if target_id:
                        commands.append((4, target_id))
                if commands:
                    record.write({field_name: commands})
            elif field.type == 'one2many':
                for child_node in field_node.findall('record'):
                    self._import_record(child_node, id_map, parent_info=(field.inverse_name, record.id), postponed_refs=postponed_refs)

        return record
