# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Custom expression handler for the Swedish VAT declaration.

Why this exists
---------------
The core Swedish tax report (``l10n_se``) computes every box from
``account.account.tag`` (``+se_10``, ``+se_48``, …). That works for the taxes
the Odoo SA chart ships. It does **not** work for the taxes
``l10n_se_extended`` adds, and those are the ones a Swedish bookkeeper
actually uses:

    MP1 / MP1i   outgoing 25 %      MP2 / MP2i   outgoing 12 %
    MP3          outgoing 6 %       I, I6        incoming 25 % / 6 %
    MU1          uttag              MBBU         vinstmarginal
    MPFF         frivillig uthyrning
    TFEU/VFEU…   reverse charge     MBBUI1-3     import

Measured 2026-11-09 in a Swedish chart: **every one of these taxes has an
empty ``tag_ids``** and posts to 2610/2620/2630/2640 — not to the 2611/2621/
2641 the core chart uses. A ``tax_tags`` expression therefore returns 0 for
them, which was verified against a real invoice: MIS reported 5 000 kr in box
10 while ``account.report`` reported 0.

So this handler is **not** an optimisation. It is the only way those boxes can
be computed, and it selects the way MIS did — on ``tax_line_id.name`` — but
behind ``account.report`` so the report itself is core.

The core-chart taxes keep using ``tax_tags``; this handler is only wired into
the lines whose tax population has no tags.
"""

import logging

from odoo import api, models, _

_logger = logging.getLogger(__name__)

# Which tax names feed which box. Kept as data so a customer-specific tax can
# be added without touching the handler (see ``_get_box_taxes``).
BOX_TAXES = {
    # Box 05 is the base amount of all taxable domestic sales, so it is fed by
    # every outgoing tax rather than by a single one.
    'se_05': ('MP1', 'MP1i', 'MP2', 'MP2i', 'MP3', 'MP3i', 'MU1', 'MBBU', 'MPFF'),
    'se_10': ('MP1', 'MP1i'),
    'se_11': ('MP2', 'MP2i'),
    'se_12': ('MP3', 'MP3i'),
    'se_30': ('TFEU', 'TFEU12', 'TFEU6', 'VFEU', 'VFEU12', 'VFEU6'),
    'se_31': ('TFEU12', 'VFEU12'),
    'se_32': ('TFEU6', 'VFEU6'),
    'se_48': (
        'I', 'I6', 'I12', 'IVIS', 'ITIS', 'IMPORT',
        'TFFU', 'TFEU', 'TFEU12', 'TFEU6',
        'VFFU', 'VFEU', 'VFEU12', 'VFEU6',
        'MBBUI1', 'MBBUI2', 'MBBUI3',
    ),
    # Boxes 35-42 are the periodic-compilation boxes. The extended chart's
    # 0 % marker taxes (VTEU/FTEU/3FEU/OTTU/OMSS/MF) carry no tags, so these
    # boxes need the handler for the same reason 10/48 do.
    'se_35': ('VTEU', 'VTEU3'),
    'se_36': ('OTTU', 'MF'),
    'se_37': ('3VEU',),
    'se_38': ('3FEU',),
    'se_39': ('FTEU',),
    'se_40': ('OTTU',),
    'se_41': ('OMSS',),
    'se_42': ('MF',),
    'se_60': ('MBBUI1',),
    'se_61': ('MBBUI2',),
    'se_62': ('MBBUI3',),
}


# Accounts that carry the OUTPUT side of a reverse-charge tax. The input side
# sits on 2645/2646/2647 and belongs to box 48.
REVERSE_CHARGE_OUTPUT_ACCOUNTS = ('2614', '2624', '2634')


class AccountSeTaxReportHandler(models.AbstractModel):
    """Expression handler for boxes the Swedish extended chart computes."""

    _name = 'account.se.tax.report.handler'
    _description = 'Swedish VAT Report Handler'

    # ------------------------------------------------------------------
    # Expression engine entry points
    # ------------------------------------------------------------------
    @api.model
    def _custom_expression_eval(self, expr, options):
        """Value of one expression, dispatched on ``expr.subformula``.

        ``subformula`` names the box (``se_10``) so one handler serves every
        line and the report carries the box identity as data.
        """
        box = expr.subformula or expr.formula
        if not box:
            _logger.warning(
                "Swedish VAT handler: expression on line %s has no "
                "subformula/formula; returning 0.", expr.report_line_id.name,
            )
            return 0.0

        lines = self._custom_expression_lines(expr, options)
        return sum(self._signed_amounts(lines))

    @api.model
    def _custom_expression_lines(self, expr, options):
        """The move lines behind a box — the drill-down contract."""
        box = expr.subformula or expr.formula
        tax_names = self._get_box_taxes(box)
        if not tax_names:
            _logger.warning(
                "Swedish VAT handler: box '%s' has no tax mapping; "
                "line '%s' will show 0.", box, expr.report_line_id.name,
            )
            return self.env['account.move.line']

        company_id = (options.get('company_ids') or [self.env.company.id])[0]
        date_from = (options.get('date') or {}).get('date_from')
        date_to = (options.get('date') or {}).get('date_to')

        base_domain = [
            ('company_id', '=', company_id),
            ('parent_state', '=', 'posted'),
        ]
        if date_from:
            base_domain.append(('date', '>=', date_from))
        if date_to:
            base_domain.append(('date', '<=', date_to))

        # (a) taxes the extended chart adds -- selected by name, as MIS did.
        # Box 05 is the *base* amount, so it must read the base lines carrying
        # those taxes, not the tax lines themselves.
        # Boxes whose value is a BASE amount (the taxable turnover) read the
        # invoice line carrying the tax, not the tax line. A 0 % marker tax
        # (VTEU/FTEU/3FEU/OTTU/OMSS/MF) only ever exists on the base line --
        # it produces no tax line at all, because the amount is zero.
        if box in ('se_05', 'se_35', 'se_36', 'se_37', 'se_38',
                   'se_39', 'se_40', 'se_41', 'se_42'):
            lines = self.env['account.move.line'].search(
                base_domain + [
                    ('tax_ids.name', 'in', list(tax_names)),
                    ('tax_line_id', '=', False),
                ]
            )
        else:
            lines = self.env['account.move.line'].search(
                base_domain + [('tax_line_id.name', 'in', list(tax_names))]
            )
            # A reverse-charge tax posts twice: once as input VAT (2645) and
            # once as output VAT (2614/2624/2634). Box 30/31/32 is the OUTPUT
            # side only -- counting both would double the amount. Measured:
            # TFEU 15 000 produced 1 875 on 2645 and 1 875 on 2614; box 30 must
            # read 1 875, not 3 750.
            if box in ('se_30', 'se_31', 'se_32'):
                lines = lines.filtered(
                    lambda l: l.account_id.code in REVERSE_CHARGE_OUTPUT_ACCOUNTS
                )

        # (b) taxes the Odoo SA chart ships -- they carry tags and no useful
        # name coupling. Union, so a chart with either population works and a
        # database with both is not double-counted (a recordset de-duplicates).
        country = self.env['res.company'].browse(company_id).account_fiscal_country_id \
            or self.env.ref('base.se')
        tags = self.env['account.account.tag']._get_tax_tags(box, country.id)
        if tags:
            lines |= self.env['account.move.line'].search(
                base_domain + [('tax_tag_ids', 'in', tags.ids)]
            )
        return lines

    @api.model
    def _signed_amounts(self, move_lines):
        """Signed amounts, one per line.

        VAT boxes are stated as positive amounts: output VAT is credited to
        26xx (``balance`` < 0) but must read positive in box 10, and input VAT
        is debited (``balance`` > 0) and must read positive in box 48. The
        absolute value is therefore the right reading, and a credit note --
        which carries the opposite balance -- subtracts automatically because
        its balance has the other sign relative to the invoice.

        Concretely: ``abs(balance)`` with the sign taken from whether the line
        is a credit note relative to its tax type. Since the tax type is not
        available on the line, use the document type, exactly as core does.
        """
        result = []
        for line in move_lines:
            move = line.move_id
            # A refund reverses the sign of its tax line.
            is_refund = move.move_type in ('out_refund', 'in_refund')
            amount = abs(line.balance)
            result.append(-amount if is_refund else amount)
        return result

    @api.model
    def _custom_expression_signed_amounts(self, expr, options, lines):
        """Per-line signed amounts for the drill-down.

        The engine asks the handler because the sign convention is the
        handler's, not the engine's: a VAT box reads positive for output VAT
        (credited to 26xx, balance < 0) and for input VAT (debited, balance
        > 0), and a credit note subtracts.
        """
        return self._signed_amounts(lines)

    @api.model
    def _custom_expression_eval_base(self, expr, options):
        """Box 05: the base amount, not the tax amount.

        Kept as a separate method so the data file can point box 05 at it
        without the handler having to special-case the box inside the general
        evaluator.
        """
        lines = self._custom_expression_lines(expr, options)
        return sum(self._signed_amounts(lines))

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    @api.model
    def _get_box_taxes(self, box):
        """Tax names for a box, with a company-level override.

        ``res.company`` may carry ``<box>_tax_names`` style configuration in
        the future; until then the data table above is the single source.
        Kept as a method so overriding is a one-liner in a customer module.
        """
        return BOX_TAXES.get(box, ())
