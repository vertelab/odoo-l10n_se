from openerp import models, fields, api,_
import sys

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .accounting_none import AccountingNone
from .data_error import DataError

if sys.version_info.major >= 3:
    unicode = str

import logging
_logger = logging.getLogger(__name__)

PROPS = [
    "color",
    "background_color",
    "font_style",
    "font_weight",
    "font_size",
    "indent_level",
    "prefix",
    "suffix",
    "dp",
    "divider",
    "hide_empty",
    "hide_always",
]

TYPE_NUM = "num"
TYPE_PCT = "pct"
TYPE_STR = "str"

CMP_DIFF = "diff"
CMP_PCT = "pct"

class MisReportKpiStyle(models.Model):

    _inherit = "mis.report.style"
    
    
    @api.model
    def to_xlsx_style(self, type, props, currency_id, use_currency_suffix, no_indent=False): #END2
        xlsx_attributes = [
            ("italic", props.font_style == "italic"),
            ("bold", props.font_weight == "bold"),
            ("size", self._font_size_to_xlsx_size.get(props.font_size, 11)),
            ("font_color", props.color),
            ("bg_color", props.background_color),
        ]
        if type == TYPE_NUM:
            num_format = "#,##0"
            if props.dp:
                num_format += "."
                num_format += "0" * props.dp
            if props.prefix:
                num_format = '"{} "{}'.format(props.prefix, num_format)
            # ~ currency = currency_id or self.env.company.currency_id#################################### använd currency id som sista utväg
            currency = currency_id
            if currency and use_currency_suffix:#######################################
                num_format = '{}" {}"'.format(num_format, currency.name)###########################################
            elif props.suffix:
                num_format = '{}" {}"'.format(num_format, props.suffix)
            xlsx_attributes.append(("num_format", num_format))
        elif type == TYPE_PCT:
            num_format = "0"
            if props.dp:
                num_format += "."
                num_format += "0" * props.dp
            num_format += "%"
            xlsx_attributes.append(("num_format", num_format))
        if props.indent_level is not None and not no_indent:
            xlsx_attributes.append(("indent", props.indent_level))
        return dict([a for a in xlsx_attributes if a[1] is not None])
    
    @api.model
    def render_currency(self, lang, style_props, type, value, currency_id, use_currency_suffix, sign="-"):
        if type == TYPE_NUM:
            return self.render_num_currency(
                lang,
                value,
                currency_id,
                use_currency_suffix,
                style_props.divider,
                style_props.dp,
                style_props.prefix,
                style_props.suffix,
                sign=sign,
            )
        elif type == TYPE_PCT:
            return self.render_pct(lang, value, style_props.dp, sign=sign)
        else:
            return self.render_str(lang, value)


    @api.model #END 1
    def render_num_currency(
        self, lang, value, currency_id, use_currency_suffix, divider=1.0, dp=0, prefix=None, suffix=None, sign="-"
    ):
        # ~ import traceback
        # ~ _logger.warning("".join(traceback.format_stack()))
        
        currency = currency_id or self.env.company.currency_id
        # format number following user language
        if value is None or value is AccountingNone:
            return ""
        value = round(value / float(divider or 1), dp or 0) or 0
        r = lang.format("%%%s.%df" % (sign, dp or 0), value, grouping=True)
        r = r.replace("-", "\N{NON-BREAKING HYPHEN}")
        if prefix:
            r = prefix + "\N{NO-BREAK SPACE}" + r
            
        # ~ currency = currency_id or self.env.company.currency_id#################################### Använd företagets som sista utväg valuta som sista utväg
        currency = currency_id
        # ~ _logger.warning("to_xlsx_style"*100)
        # ~ _logger.warning(f"self.name={self}")
        # ~ _logger.warning(f"use_currency_suffix = {use_currency_suffix}")
        # ~ _logger.warning(f"currency = {currency}")
        if currency and use_currency_suffix:#######################################
            r = r + "\N{NO-BREAK SPACE}" + currency.name
        elif suffix:
            r = r + "\N{NO-BREAK SPACE}" + suffix
        return r
        
        
        
