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
    def to_xlsx_style(self, type, props, currency_id, no_indent=False): #END2
        import traceback
        _logger.warning("".join(traceback.format_stack()))
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
            if props.suffix:
                _logger.warning(f"excel suffix {props.suffix}")
                _logger.warning(f"{currency_id=}")
                num_format = '{}" {}"'.format(num_format, currency_id.name)
                # ~ num_format = '{}" {}"'.format(num_format, props.suffix) ###################
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
    def render(self, lang, style_props, type, value, currency_id, sign="-"):
        if type == TYPE_NUM:
            return self.render_num(
                lang,
                value,
                currency_id,
                style_props.divider,
                style_props.dp,
                style_props.prefix,
                style_props.suffix,
                sign=sign,
            )
        elif type == TYPE_PCT:
            return self.render_pct(lang, value, currency_id, style_props.dp, sign=sign)
        else:
            return self.render_str(lang, value)


    @api.model
    def render_pct(self, lang, value, currency_id, dp=1, sign="-"):
        return self.render_num(lang, value, currency_id, divider=0.01, dp=dp, suffix="%", sign=sign)

    @api.model #END 1
    def render_num(
        self, lang, value, currency_id, divider=1.0, dp=0, prefix=None, suffix=None, sign="-"
    ):
        
        currency = currency_id or self.env.company.currency_id
        # format number following user language
        if value is None or value is AccountingNone:
            return ""
        value = round(value / float(divider or 1), dp or 0) or 0
        r = lang.format("%%%s.%df" % (sign, dp or 0), value, grouping=True)
        r = r.replace("-", "\N{NON-BREAKING HYPHEN}")
        if prefix:
            r = prefix + "\N{NO-BREAK SPACE}" + r
        # ~ if currency_suffix:
        r = r + "\N{NO-BREAK SPACE}" + currency.name
        # ~ if suffix:
            # ~ r = r + "\N{NO-BREAK SPACE}" + suffix
        return r
        
        
        
