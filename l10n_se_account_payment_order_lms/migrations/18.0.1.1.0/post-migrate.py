# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Unpublish the generation-1 payment course (T/10526).

The course content is loaded with noupdate="1", so flipping is_published in
the XML only affects fresh installs. This migration reaches the existing
records in an upgraded database: channel plus every slide in it.

The module stays installed as a reference; nothing is deleted.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    channel = env.ref(
        "l10n_se_account_payment_order_lms.slide_channel_payment_pending",
        raise_if_not_found=False,
    )
    if not channel:
        _logger.warning("Payment LMS: channel xmlid not found, nothing to do")
        return

    slides = channel.slide_ids
    published_slides = slides.filtered("is_published")
    if published_slides:
        published_slides.write({"is_published": False})
    if channel.is_published:
        channel.write({"is_published": False})

    _logger.info(
        "Payment LMS: unpublished generation-1 channel %r and %s slide(s)",
        channel.name, len(published_slides),
    )
