from .accounting_none import AccountingNone
from odoo.addons.mis_builder.models.mis_safe_eval import DataError, mis_safe_eval
from odoo.addons.mis_builder.models.kpimatrix import KpiMatrix

import logging
_logger = logging.getLogger(__name__)


class KpiMatrixRow(object):

    # TODO: ultimately, the kpi matrix will become ignorant of KPI's and
    #       accounts and know about rows, columns, sub columns and styles only.
    #       It is already ignorant of period and only knowns about columns.
    #       This will require a correct abstraction for expanding row details.

    def __init__(self, matrix, kpi, account_id=None, parent_row=None):
        self._matrix = matrix
        self.kpi = kpi
        self.account_id = account_id
        self.description = ""
        self.parent_row = parent_row
        if not self.account_id:
            self.style_props = self._matrix._style_model.merge(
                [self.kpi.report_id.style_id, self.kpi.style_id]
            )
        else:
            self.style_props = self._matrix._style_model.merge(
                [self.kpi.report_id.style_id, self.kpi.auto_expand_accounts_style_id]
            )

    @property
    def label(self):
        if not self.account_id:
            return self.kpi.description
        else:
            return self._matrix.get_account_name(self.account_id)

    @property
    def row_id(self):
        if not self.account_id:
            return self.kpi.name
        else:
            return "{}:{}".format(self.kpi.name, self.account_id)

    def iter_cell_tuples(self, cols=None):
        if cols is None:
            cols = self._matrix.iter_cols()
        for col in cols:
            yield col.get_cell_tuple_for_row(self)

    def iter_cells(self, subcols=None):
        if subcols is None:
            subcols = self._matrix.iter_subcols()
        for subcol in subcols:
            yield subcol.get_cell_for_row(self)

    def is_empty(self):
        for cell in self.iter_cells():
            if cell and cell.val not in (AccountingNone, None):
                return False
        return True


class KpiMatrixCell(object):  # noqa: B903 (immutable data class)
    def __init__(
        self,
        row,
        subcol,
        val,
        val_rendered,
        val_comment,
        style_props,
        drilldown_arg,
        val_type,
    ):
        self.row = row
        self.subcol = subcol
        self.val = val
        self.val_rendered = val_rendered
        self.val_comment = val_comment
        self.style_props = style_props
        self.drilldown_arg = drilldown_arg
        self.val_type = val_type

class KpiMatrixExtended(KpiMatrix):

    def as_dict(self, hide_lines_that_are_empty):
        header = [{"cols": []}, {"cols": []}]
        for col in self.iter_cols():
            header[0]["cols"].append(
                {
                    "label": col.label,
                    "description": col.description,
                    "colspan": col.colspan,
                }
            )
            for subcol in col.iter_subcols():
                header[1]["cols"].append(
                    {
                        "label": subcol.label,
                        "description": subcol.description,
                        "colspan": 1,
                    }
                )

        body = []
        for row in self.iter_rows():
            if (row.style_props.hide_empty and row.is_empty()) or row.style_props.hide_always or (row.is_empty() and row.kpi.type != "str" and hide_lines_that_are_empty):
                continue
            row_data = {
                "row_id": row.row_id,
                "parent_row_id": (row.parent_row and row.parent_row.row_id or None),
                "label": row.label,
                "description": row.description,
                "style": self._style_model.to_css_style(row.style_props),
                "cells": [],
            }
            for cell in row.iter_cells():
                if cell is None:
                    # TODO use subcol style here
                    row_data["cells"].append({})
                else:
                    if cell.val is AccountingNone or isinstance(cell.val, DataError):
                        val = None
                    else:
                        val = cell.val
                    col_data = {
                        "val": val,
                        "val_r": cell.val_rendered,
                        "val_c": cell.val_comment,
                        "style": self._style_model.to_css_style(
                            cell.style_props, no_indent=True
                        ),
                    }
                    if cell.drilldown_arg:
                        col_data["drilldown_arg"] = cell.drilldown_arg
                    row_data["cells"].append(col_data)
            body.append(row_data)

        return {"header": header, "body": body}
        
    def set_values(self, kpi, col_key, vals, drilldown_args, currency_id, use_currency_suffix, tooltips=True):
        """Set values for a kpi and a colum.

        Invoke this after declaring the kpi and the column.
        """
        self.set_values_detail_account(
            kpi, col_key, None, vals, drilldown_args, currency_id, use_currency_suffix, tooltips
        )
        
    def set_values_detail_account(
        self, kpi, col_key, account_id, vals, drilldown_args, currency_id, use_currency_suffix, tooltips=True
        ):
        """Set values for a kpi and a column and a detail account.

        Invoke this after declaring the kpi and the column.
        """
        if not account_id:
            row = self._kpi_rows[kpi]
        else:
            kpi_row = self._kpi_rows[kpi]
            if account_id in self._detail_rows[kpi]:
                row = self._detail_rows[kpi][account_id]
            else:
                row = KpiMatrixRow(self, kpi, account_id, parent_row=kpi_row)
                self._detail_rows[kpi][account_id] = row
        col = self._cols[col_key]
        cell_tuple = []
        assert len(vals) == col.colspan
        assert len(drilldown_args) == col.colspan
        for val, drilldown_arg, subcol in zip(vals, drilldown_args, col.iter_subcols()):
            if isinstance(val, DataError):
                val_rendered = val.name
                val_comment = val.msg
            else:
                
                val_rendered = self._style_model.render(
                    self.lang, row.style_props, kpi.type, val, currency_id, use_currency_suffix
                )
                if row.kpi.multi and subcol.subkpi:
                    val_comment = "{}.{} = {}".format(
                        row.kpi.name,
                        subcol.subkpi.name,
                        row.kpi._get_expression_str_for_subkpi(subcol.subkpi),
                    )
                else:
                    val_comment = "{} = {}".format(row.kpi.name, row.kpi.expression)
            cell_style_props = row.style_props
            if row.kpi.style_expression:
                # evaluate style expression
                try:
                    style_name = mis_safe_eval(
                        row.kpi.style_expression, col.locals_dict
                    )
                except Exception:
                    _logger.error(
                        "Error evaluating style expression <%s>",
                        row.kpi.style_expression,
                        exc_info=True,
                    )
                if style_name:
                    style = self._style_model.search([("name", "=", style_name)])
                    if style:
                        cell_style_props = self._style_model.merge(
                            [row.style_props, style[0]]
                        )
                    else:
                        _logger.error("Style '%s' not found.", style_name)
            cell = KpiMatrixCell(
                row,
                subcol,
                val,
                val_rendered,
                tooltips and val_comment or None,
                cell_style_props,
                drilldown_arg,
                kpi.type,
            )
            cell_tuple.append(cell)
        assert len(cell_tuple) == col.colspan
        col._set_cell_tuple(row, cell_tuple)        
