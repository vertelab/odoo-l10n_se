# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Sveriges Riksbank as a currency rate provider.

Riksbank publishes one observation series per currency, named
``SEK<CUR>PMI`` (``SEKEURPMI``, ``SEKUSDPMI``, ...), holding the value of
one foreign unit in SEK.

Two endpoints are used:

* ``/Observations/Latest/<series>`` for a single day.
* ``/Observations/<series>/<from>/<to>`` for a date range.

The series always comes first and a comma separated list of series is
rejected, so one request per currency is needed. Riksbank rate limits the
API to roughly one request every five to ten seconds and answers HTTP 429
with a ``Try again in N seconds`` message when the limit is exceeded.
"""

import logging
import re
import time
from datetime import date

import requests
from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

#: Seconds to wait between two series. Riksbank allows about one request
#: every five to ten seconds; eight stays inside that window.
RIKSBANK_REQUEST_DELAY = 8

#: Attempts per series when Riksbank answers 429.
RIKSBANK_MAX_ATTEMPTS = 3

#: Fallback wait when the 429 body carries no usable retry hint.
RIKSBANK_DEFAULT_RETRY_DELAY = 10

#: Riksbank's own ceiling on a single series id.
RIKSBANK_MAX_SERIES_LENGTH = 25


class ResCurrencyRateProviderRiksbank(models.Model):
    _inherit = "res.currency.rate.provider"

    service = fields.Selection(
        selection_add=[("riksbank", "Riksbank Sweden")],
        ondelete={"riksbank": "set default"},
    )

    def _get_supported_currencies(self):
        self.ensure_one()
        if self.service != "riksbank":
            return super()._get_supported_currencies()  # pragma: no cover

        # Currencies Riksbank publishes a SEK<CUR>PMI series for. SEK is the
        # base currency and is never fetched.
        return [
            "AUD",
            "BRL",
            "CAD",
            "CHF",
            "CNY",
            "CZK",
            "DKK",
            "EUR",
            "GBP",
            "HKD",
            "HUF",
            "IDR",
            "INR",
            "JPY",
            "KRW",
            "MXN",
            "MYR",
            "NOK",
            "NZD",
            "PHP",
            "PLN",
            "RON",
            "SGD",
            "THB",
            "TRY",
            "USD",
            "ZAR",
        ]

    def _obtain_rates(self, base_currency, currencies, date_from, date_to):
        self.ensure_one()
        if self.service != "riksbank":
            return super()._obtain_rates(
                base_currency, currencies, date_from, date_to
            )  # pragma: no cover

        series_currencies = self._get_riksbank_series_currencies(
            base_currency, currencies
        )
        if not series_currencies:
            return {}

        rates = {}
        for index, currency in enumerate(series_currencies):
            if index:
                time.sleep(RIKSBANK_REQUEST_DELAY)
            for rate_date, value in self._fetch_riksbank_series(
                currency, date_from, date_to
            ):
                # Riksbank quotes SEK per foreign unit, res.currency.rate
                # stores the inverse. See the module description.
                rates.setdefault(rate_date, {})[currency] = 1.0 / value
        return rates

    def _get_riksbank_series_currencies(self, base_currency, currencies):
        """Currencies to request series for, given the company currency."""
        self.ensure_one()
        supported = self._get_supported_currencies()
        wanted = [
            currency
            for currency in currencies
            if currency != base_currency and currency in supported
        ]
        if base_currency == "SEK":
            return wanted

        # The company currency is not SEK. Riksbank only quotes against SEK,
        # so the cross rate needs the base currency series as well.
        if base_currency not in supported:
            raise UserError(
                _(
                    "Riksbank does not publish a rate for the company currency "
                    "%(currency)s. Set up the provider on a company whose "
                    "currency is SEK, or pick another provider.",
                    currency=base_currency,
                )
            )
        return wanted + [base_currency]

    def _fetch_riksbank_series(self, currency, date_from, date_to):
        """Return [(iso_date, sek_per_unit)] for one currency series."""
        self.ensure_one()
        series = f"SEK{currency}PMI"
        if len(series) > RIKSBANK_MAX_SERIES_LENGTH:  # pragma: no cover
            raise UserError(
                _("Invalid Riksbank series name: %(series)s", series=series)
            )

        latest_url = self._get_riksbank_url(f"Observations/Latest/{series}")
        range_url = self._get_riksbank_url(
            f"Observations/{series}/{date_from.isoformat()}/{date_to.isoformat()}"
        )

        if date_from == date_to:
            payload = self._request_riksbank(latest_url)
            observations = [payload] if isinstance(payload, dict) else []
        else:
            payload = self._request_riksbank(range_url)
            observations = payload if isinstance(payload, list) else []

        result = []
        for observation in observations:
            value = observation.get("value")
            if value in (None, 0):
                # Riksbank publishes no rate on weekends and holidays; the
                # range endpoint leaves those days out entirely.
                continue
            rate_date = date.fromisoformat(observation["date"])
            if date_from and rate_date < date_from:
                continue
            if date_to and rate_date > date_to:
                continue
            result.append((rate_date.isoformat(), float(value)))
        return result

    def _get_riksbank_url(self, path):
        self.ensure_one()
        # Overridable for tests and for pointing at a mirror.
        base_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("l10n_se_currency_riksbank.base_url")
            or "https://api.riksbank.se/swea/v1"
        )
        return f"{base_url.rstrip('/')}/{path}"

    def _request_riksbank(self, url):
        """GET a Riksbank URL, retrying on 429 up to RIKSBANK_MAX_ATTEMPTS."""
        self.ensure_one()
        last_error = None
        for attempt in range(RIKSBANK_MAX_ATTEMPTS):
            try:
                response = requests.get(url, timeout=30)
            except requests.RequestException as error:
                raise UserError(
                    _(
                        "Could not reach Riksbank: %(error)s",
                        error=error,
                    )
                ) from error

            if response.status_code == 429:
                delay = self._get_riksbank_retry_delay(response, attempt)
                _logger.info(
                    "Riksbank rate limit hit (attempt %s/%s), waiting %s s",
                    attempt + 1,
                    RIKSBANK_MAX_ATTEMPTS,
                    delay,
                )
                last_error = response
                time.sleep(delay)
                continue

            if response.status_code != 200:
                raise UserError(
                    _(
                        "Riksbank answered %(status)s for %(url)s",
                        status=response.status_code,
                        url=url,
                    )
                )
            return response.json()

        # ``last_error`` is a Response, not an exception, so it cannot be
        # chained with ``from``. Put the last status in the message instead.
        raise UserError(
            _(
                "Riksbank kept answering 429 Too Many Requests for %(url)s "
                "after %(attempts)s attempts. Try again later.",
                url=url,
                attempts=RIKSBANK_MAX_ATTEMPTS,
            )
        )

    def _get_riksbank_retry_delay(self, response, attempt):
        """Seconds to wait: the hint in the 429 body, else a growing wait."""
        try:
            message = response.json().get("message") or ""
        except ValueError:
            message = ""
        match = re.search(r"(\d+)\s*second", message, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return RIKSBANK_DEFAULT_RETRY_DELAY * (attempt + 1)
