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
    export_mode = fields.Selection([
        ('wizard', 'Wizard Import (XML)'),
        ('data', 'Module Data File (XML)')
    ], string='Export Mode', default='wizard', required=True,
       help="Wizard Import: For use with this module's import feature.\n"
            "Module Data File: Standard Odoo XML to include in a module's data folder.")

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

        if self.export_mode == 'wizard':
            xml_content = self._generate_wizard_xml()
            filename = f'mis_wizard_import_{fields.Date.today()}.xml'
        else:
            xml_content = self._generate_data_file_xml()
            filename = f'mis_data_file_{fields.Date.today()}.xml'

        # Create attachment and return download action
        attachment = self.env['ir.attachment'].create({
            'name': filename,
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
                'name', 'description', 'report_id', 'target_move', 'date',
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

    def _generate_wizard_xml(self):
        """Generates XML for the wizard-based import (nested records)."""
        root = ET.Element('mis_report_export', version="1.0")
        ET.SubElement(root, 'export_date').text = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        exported_records = {}
        data_exported = set()
        
        styles_root = ET.SubElement(root, 'styles')
        templates_root = ET.SubElement(root, 'templates')
        instances_root = ET.SubElement(root, 'instances')

        config = self._get_export_config()
        for instance in self.instance_ids:
            self._export_record_wizard(instances_root, instance, config, exported_records, styles_root, templates_root, data_exported)

        return self._format_xml(root)

    def _export_record_wizard(self, parent_elem, record, config, exported_records, styles_root, templates_root, data_exported):
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
            xml_id = exported_records.get(rec_key) or self._make_export_xml_id(record, prefix="")
            record_elem.set('xml_id', xml_id)
            exported_records[rec_key] = xml_id

        fields_to_export = config.get(model_name, [])
        for field_name in fields_to_export:
            field = record._fields.get(field_name)
            if not field: continue
            val = record[field_name]
            if not val and field.type != 'boolean': continue

            field_elem = ET.SubElement(record_elem, 'field', name=field_name)
            if field.type in ('char', 'text', 'html', 'selection', 'integer', 'float'):
                field_elem.text = str(val)
            elif field.type == 'boolean':
                field_elem.text = 'True' if val else 'False'
            elif field.type == 'many2one':
                if field.comodel_name in config:
                    target_key = (field.comodel_name, val.id)
                    if target_key not in data_exported:
                        if field.comodel_name == 'mis.report.style':
                            self._export_record_wizard(styles_root, val, config, exported_records, styles_root, templates_root, data_exported)
                        elif field.comodel_name == 'mis.report':
                            self._export_record_wizard(templates_root, val, config, exported_records, styles_root, templates_root, data_exported)
                    target_id = exported_records.get(target_key)
                    if target_id:
                        field_elem.set('ref' if '.' in target_id else 'xml_ref', target_id)
                elif field.comodel_name in ('ir.model', 'ir.model.fields'):
                    field_elem.text = val.model if field.comodel_name == 'ir.model' else f"{val.model_id.model}.{val.name}"
                else:
                    ext_id = val.get_external_id().get(val.id)
                    if ext_id: field_elem.set('ref', ext_id)
                    elif 'name' in val._fields: field_elem.set('search', f"[('name', '=', '{val.name}')]")
            elif field.type in ('one2many', 'many2many'):
                if field.type == 'many2many' and field.comodel_name == 'ir.model.fields':
                    for c in val: ET.SubElement(field_elem, 'value').text = f"{c.model_id.model}.{c.name}"
                elif field.type == 'many2many' and field.comodel_name in config:
                    for c in val:
                        t_id = exported_records.get((field.comodel_name, c.id))
                        if t_id:
                            node = ET.SubElement(field_elem, 'record_ref')
                            node.set('ref' if '.' in t_id else 'xml_ref', t_id)
                else:
                    for c in val: self._export_record_wizard(field_elem, c, config, exported_records, styles_root, templates_root, data_exported)

    def _generate_data_file_xml(self):
        """Generates a standard Odoo Data XML file (flat records)."""
        root = ET.Element('odoo')
        data_node = ET.SubElement(root, 'data', noupdate="1")
        
        config = self._get_export_config()
        all_records = [] # List of (record, parent_record, parent_field)
        exported_ids = {} # (model, id) -> xml_id
        collected_keys = set()
        
        # 1. Collect all records recursively
        for instance in self.instance_ids:
            self._collect_records_data(
                instance, config, all_records, exported_ids, collected_keys,
                force_export=True,
            )
            
        # 2. Export each record that needs definition, after its dependencies
        for record, parent, p_field in self._sort_records_for_data_export(
            all_records, config, exported_ids,
        ):
            self._export_record_data(data_node, record, config, exported_ids, parent, p_field)

        return self._format_xml(root)

    def _collect_records_data(
        self, record, config, all_records, exported_ids, collected_keys,
        parent=None, parent_field=None, force_export=False,
    ):
        model_name = record._name
        rec_key = (model_name, record.id)
        if rec_key in collected_keys:
            return

        # Check for real External ID
        ext_id = record.get_external_id().get(record.id)
        if ext_id and not force_export:
            exported_ids[rec_key] = ext_id
            # Do NOT collect body of records that are already in a module
            return

        # Generate unique ID for new record
        xml_id = self._make_export_xml_id(record)
        exported_ids[rec_key] = xml_id
        collected_keys.add(rec_key)
        all_records.append((record, parent, parent_field))

        # Explore relations
        fields_to_export = config.get(model_name, [])
        for f_name in fields_to_export:
            field = record._fields.get(f_name)
            if not field: continue
            val = record[f_name]
            if not val: continue

            if field.type == 'many2one' and field.comodel_name in config:
                self._collect_records_data(
                    val, config, all_records, exported_ids, collected_keys,
                )
            elif field.type == 'one2many' and field.comodel_name in config:
                for c in val:
                    self._collect_records_data(
                        c, config, all_records, exported_ids, collected_keys,
                        parent=record, parent_field=field.inverse_name,
                        force_export=True,
                    )
            elif field.type == 'many2many' and field.comodel_name in config:
                if field.comodel_name != 'ir.model.fields':
                    for c in val:
                        self._collect_records_data(
                            c, config, all_records, exported_ids, collected_keys,
                        )

    def _sort_records_for_data_export(self, all_records, config, exported_ids):
        """Sort records so standard XML refs point to already-created records."""
        record_map = {}
        for item in all_records:
            record = item[0]
            record_map[(record._name, record.id)] = item
        remaining = list(all_records)
        emitted = set()
        ordered = []

        def is_local_record(key):
            xml_id = exported_ids.get(key)
            return xml_id and '.' not in xml_id and key in record_map

        def dependencies(item):
            record, parent, parent_field = item
            deps = set()
            if parent:
                parent_key = (parent._name, parent.id)
                if is_local_record(parent_key):
                    deps.add(parent_key)

            for f_name in config.get(record._name, []):
                if f_name == parent_field:
                    continue
                field = record._fields.get(f_name)
                if not field:
                    continue
                val = record[f_name]
                if not val:
                    continue

                if field.type == 'many2one' and field.comodel_name in config:
                    dep_key = (field.comodel_name, val.id)
                    if dep_key != (record._name, record.id) and is_local_record(dep_key):
                        deps.add(dep_key)
                elif field.type == 'many2many' and field.comodel_name in config:
                    for target in val:
                        dep_key = (field.comodel_name, target.id)
                        if dep_key != (record._name, record.id) and is_local_record(dep_key):
                            deps.add(dep_key)
            return deps

        while remaining:
            progressed = False
            for item in list(remaining):
                record = item[0]
                rec_key = (record._name, record.id)
                if dependencies(item).issubset(emitted):
                    ordered.append(item)
                    emitted.add(rec_key)
                    remaining.remove(item)
                    progressed = True
            if not progressed:
                _logger.warning(
                    "Could not fully order MIS export records due to cyclic references: %s",
                    [(item[0]._name, item[0].id) for item in remaining],
                )
                ordered.extend(remaining)
                break
        return ordered

    def _export_record_data(self, data_node, record, config, exported_ids, parent=None, p_field=None):
        model_name = record._name
        xml_id = exported_ids.get((model_name, record.id))
        
        # If it contains a dot, it's a reference to an existing module record
        if '.' in xml_id:
            return

        record_elem = ET.SubElement(data_node, 'record', model=model_name, id=xml_id)
        written_fields = set()

        if parent and p_field:
            parent_xml_id = exported_ids.get((parent._name, parent.id))
            if parent_xml_id:
                field_elem = ET.SubElement(record_elem, 'field', name=p_field)
                field_elem.set('ref', parent_xml_id)
                written_fields.add(p_field)
        
        fields_to_export = config.get(model_name, [])
        for f_name in fields_to_export:
            if f_name in written_fields:
                continue
            field = record._fields.get(f_name)
            if not field: continue
            val = record[f_name]
            if not val and field.type != 'boolean': continue

            if field.type in ('char', 'text', 'html', 'selection', 'integer', 'float', 'monetary', 'date', 'datetime'):
                field_elem = ET.SubElement(record_elem, 'field', name=f_name)
                field_elem.text = str(val)
            elif field.type == 'boolean':
                field_elem = ET.SubElement(record_elem, 'field', name=f_name)
                field_elem.text = 'True' if val else 'False'
            elif field.type == 'many2one':
                if field.comodel_name in config:
                    target_id = exported_ids.get((field.comodel_name, val.id))
                    if target_id:
                        field_elem = ET.SubElement(record_elem, 'field', name=f_name)
                        field_elem.set('ref', target_id)
                elif field.comodel_name == 'ir.model':
                    field_elem = ET.SubElement(record_elem, 'field', name=f_name)
                    ext_id = val.get_external_id().get(val.id)
                    if ext_id:
                        field_elem.set('ref', ext_id)
                    else:
                        field_elem.set('search', repr([('model', '=', val.model)]))
                elif field.comodel_name == 'ir.model.fields':
                    field_elem = ET.SubElement(record_elem, 'field', name=f_name)
                    ext_id = val.get_external_id().get(val.id)
                    if ext_id:
                        field_elem.set('ref', ext_id)
                    else:
                        field_elem.set('search', repr([
                            ('model', '=', val.model_id.model),
                            ('name', '=', val.name),
                        ]))
                else:
                    ext_id = val.get_external_id().get(val.id)
                    if ext_id:
                        field_elem = ET.SubElement(record_elem, 'field', name=f_name)
                        field_elem.set('ref', ext_id)
                    elif 'name' in val._fields:
                        field_elem = ET.SubElement(record_elem, 'field', name=f_name)
                        field_elem.set('search', repr([('name', '=', val.name)]))
            elif field.type == 'one2many':
                # Standard module data is more robust when One2many children are
                # exported as their own records with the inverse Many2one set.
                continue
            elif field.type == 'many2many':
                if field.comodel_name == 'ir.model.fields':
                    field_elem = ET.SubElement(record_elem, 'field', name=f_name)
                    field_elem.set('search', repr(self._model_fields_domain(val)))
                elif field.comodel_name in config:
                    ref_ids = []
                    for c in val:
                        t_id = exported_ids.get((field.comodel_name, c.id))
                        if t_id: ref_ids.append(t_id)
                    if ref_ids:
                        field_elem = ET.SubElement(record_elem, 'field', name=f_name)
                        eval_str = "[(6, 0, [%s])]" % ", ".join([f"ref('{rid}')" for rid in ref_ids])
                        field_elem.set('eval', eval_str)

    def _model_fields_domain(self, fields_records):
        """Return a portable domain for an ir.model.fields recordset."""
        terms = []
        for field in fields_records:
            terms.extend([
                '&',
                ('model', '=', field.model_id.model),
                ('name', '=', field.name),
            ])
        if len(fields_records) <= 1:
            return terms[1:] if terms else []
        return ['|'] * (len(fields_records) - 1) + terms

    def _make_export_xml_id(self, record, prefix="export_"):
        name = record.display_name if 'display_name' in record._fields else False
        if not name and 'name' in record._fields:
            name = record.name
        name_slug = self._slugify_xml_id_part(name or "")
        model_slug = record._name.replace('.', '_')
        if name_slug:
            return f"{prefix}{model_slug}_{name_slug}_{record.id}"
        return f"{prefix}{model_slug}_{record.id}"

    def _slugify_xml_id_part(self, value):
        value = re.sub(r'[^0-9A-Za-z_]+', '_', str(value).lower()).strip('_')
        value = re.sub(r'_+', '_', value)
        if value and value[0].isdigit():
            value = f"x_{value}"
        return value[:60].rstrip('_')

    def _format_xml(self, root):
        rough_string = ET.tostring(root, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        xml_content = reparsed.toprettyxml(indent="    ", encoding='utf-8').decode('utf-8')
        return re.sub(r'(\n[ \t]*</record>)(\n[ \t]*<record\b)', r'\1\n\2', xml_content)

    def action_import(self):
        if not self.data_file:
            raise UserError(_("Please select a file to import."))
        try:
            xml_content = base64.b64decode(self.data_file)
            root = ET.fromstring(xml_content)
            id_map = {}
            postponed_refs = []
            
            # This import logic only works for 'wizard' format (nested)
            # but we can try to make it work for flat 'data' format too if needed.
            # For now, we follow the tiered pass structure.
            for tier in ['styles', 'templates', 'instances']:
                node = root.find(tier)
                if node is not None:
                    for r_node in node.findall('record'):
                        self._import_record(r_node, id_map, postponed_refs=postponed_refs)
            
            # Final pass
            for record, field_name, xml_ref in postponed_refs:
                if xml_ref in id_map: record.write({field_name: id_map[xml_ref].id})

            return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
                'title': _('Import Successful'), 'message': _('MIS Reports imported successfully!'), 'type': 'success', 'sticky': False}}
        except Exception as e:
            _logger.error("Import failed: %s", str(e), exc_info=True)
            raise UserError(_("Import failed: %s") % str(e))

    def _import_record(self, record_node, id_map, parent_info=None, postponed_refs=None):
        model_name = record_node.get('model')
        xml_id = record_node.get('id') or record_node.get('xml_id')
        data = {parent_info[0]: parent_info[1]} if parent_info else {}
        relational_data = []

        for f_node in record_node.findall('field'):
            f_name = f_node.get('name')
            field = self.env[model_name]._fields.get(f_name)
            if not field: continue
            if field.type in ('one2many', 'many2many'):
                relational_data.append((f_name, f_node))
                continue
            
            ref, xml_ref, search = f_node.get('ref'), f_node.get('xml_ref'), f_node.get('search')
            if ref:
                r = self.env.ref(ref, raise_if_not_found=False)
                if r: data[f_name] = r.id
            elif xml_ref:
                if xml_ref in id_map: data[f_name] = id_map[xml_ref].id
            elif search:
                try:
                    import ast
                    domain = ast.literal_eval(search)
                    r = self.env[field.comodel_name].search(domain, limit=1)
                    if r: data[f_name] = r.id
                except: pass
            elif field.type == 'many2one':
                if field.comodel_name == 'ir.model':
                    r = self.env['ir.model'].search([('model', '=', f_node.text)])
                    if r: data[f_name] = r.id
                elif field.comodel_name == 'ir.model.fields':
                    if f_node.text and '.' in f_node.text:
                        m, f = f_node.text.split('.')
                        r = self.env['ir.model.fields'].search([('model', '=', m), ('name', '=', f)])
                        if r: data[f_name] = r.id
            else:
                if field.type == 'boolean': data[f_name] = f_node.text == 'True'
                elif field.type == 'integer': data[f_name] = int(f_node.text) if f_node.text else 0
                elif field.type == 'float': data[f_name] = float(f_node.text) if f_node.text else 0.0
                else: data[f_name] = f_node.text

        record = None
        if xml_id and not record_node.get('xml_id'):
            record = self.env.ref(xml_id, raise_if_not_found=False)
        if not record:
            name = data.get('name')
            if name:
                dom = [('name', '=', name)]
                if parent_info and model_name not in ('mis.report', 'mis.report.instance', 'mis.report.style'):
                    dom.append((parent_info[0], '=', parent_info[1]))
                record = self.env[model_name].search(dom, limit=1)
        if record: record.write(data)
        else: record = self.env[model_name].create(data)

        if xml_id: id_map[xml_id] = record
        if postponed_refs is not None:
            for f_node in record_node.findall('field'):
                xr = f_node.get('xml_ref')
                if xr and xr not in id_map: postponed_refs.append((record, f_node.get('name'), xr))

        for f_name, f_node in relational_data:
            field = record._fields.get(f_name)
            if field.type == 'many2many' and field.comodel_name == 'ir.model.fields':
                cmds = []
                for v in f_node.findall('value'):
                    if v.text and '.' in v.text:
                        m, f = v.text.split('.')
                        r = self.env['ir.model.fields'].search([('model', '=', m), ('name', '=', f)])
                        if r: cmds.append((4, r.id))
                if cmds: record.write({f_name: cmds})
            elif field.type == 'many2many' and field.comodel_name in self._get_export_config():
                cmds = []
                for rn in f_node.findall('record_ref'):
                    target_id = None
                    if rn.get('ref'):
                        r = self.env.ref(rn.get('ref'), raise_if_not_found=False)
                        if r: target_id = r.id
                    elif rn.get('xml_ref') and rn.get('xml_ref') in id_map:
                        target_id = id_map[rn.get('xml_ref')].id
                    if target_id: cmds.append((4, target_id))
                if cmds: record.write({f_name: cmds})
            elif field.type == 'one2many':
                for cn in f_node.findall('record'):
                    self._import_record(cn, id_map, parent_info=(field.inverse_name, record.id), postponed_refs=postponed_refs)
        return record
