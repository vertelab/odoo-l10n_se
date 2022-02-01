from .accounting_none import AccountingNone
from odoo.addons.mis_builder.models.mis_safe_eval import DataError, mis_safe_eval
from odoo.addons.mis_builder.models.kpimatrix import KpiMatrix

import logging
_logger = logging.getLogger(__name__)

class KpiMatrixExtended(KpiMatrix):

    def as_dict(self, hide_lines_that_are_empty):
        #_logger.warning("JAKMAR AS_DICT METHOD OVERRIDEN")
        #_logger.warning(f"{hide_lines_that_are_empty=}")
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
            #_logger.warning(f"{row.__dict__}")
            #_logger.warning(f"{row.kpi.type}")
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
