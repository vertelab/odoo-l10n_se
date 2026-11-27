from odoo import models
from odoo.tools.sql import table_exists


class MisReportInstanceAnnotation(models.Model):
    _inherit = "mis.report.instance.annotation"

    def init(self):
        if table_exists(self.env.cr, self._table):
            super().init()
