from odoo import models


class MisReportKpi(models.Model):
    _inherit = "mis.report.kpi"

    def _get_expressions(self, subkpis):
        if subkpis and self.multi:
            return [self._get_expression_for_subkpi(subkpi) for subkpi in subkpis]
        else:
            if not self.expression_ids:
                return [None]
            expressions = self.expression_ids.filtered(lambda e: not e.subkpi_id)
            if expressions:
                return expressions[:1]
            return [None]
