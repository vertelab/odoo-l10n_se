from odoo.addons.mis_builder.models.expression_evaluator import ExpressionEvaluator

try:
    import itertools.izip as zip
except ImportError:
    pass  # python 3


class ExpressionEvaluatorExtended(ExpressionEvaluator):
    def __init__(
            self, aep, date_from, date_to, additional_move_line_filter=None, aml_model=None, target_move=None,
            find_moves_by_period=False, accounting_method='Invoice',
    ):
        # Call the parent class constructor to initialize it
        super(ExpressionEvaluatorExtended, self).__init__(
            aep, date_from, date_to, additional_move_line_filter, aml_model
        )

        self.target_move = target_move
        self.find_moves_by_period = find_moves_by_period
        self.accounting_method = accounting_method

    def aep_do_queries(self):
        if self.aep and not self._aep_queries_done:
            print(self.aml_model)
            self.aep.do_queries(
                self.date_from,
                self.date_to,
                self.additional_move_line_filter,
                self.aml_model,
                self.target_move,
                find_moves_by_period=self.find_moves_by_period,
                accounting_method=self.accounting_method
            )
            self._aep_queries_done = True
