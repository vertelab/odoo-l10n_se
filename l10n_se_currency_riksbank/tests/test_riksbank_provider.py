# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Riksbank provider tests.

Every HTTP call is mocked. Riksbank rate limits the API to about one
request every five to ten seconds, so the suite must never reach the
network.
"""

from datetime import date
from unittest import mock

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

_module_ns = "odoo.addons.l10n_se_currency_riksbank"
_file_ns = _module_ns + ".models.res_currency_rate_provider_riksbank"
_provider_class = _file_ns + ".ResCurrencyRateProviderRiksbank"
_requests_get = _file_ns + ".requests.get"


class FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload


@tagged("post_install", "-at_install", "l10n_se_currency_riksbank")
class TestRiksbankProvider(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({
            "name": "Riksbank test AB",
            "currency_id": cls.env.ref("base.SEK").id,
        })
        cls.Provider = cls.env["res.currency.rate.provider"].with_company(
            cls.company
        )
        cls.provider = cls.Provider.create({
            "company_id": cls.company.id,
            "service": "riksbank",
            "currency_ids": [(6, 0, [
                cls.env.ref("base.EUR").id,
                cls.env.ref("base.USD").id,
            ])],
        })

    def _patch_get(self, side_effect):
        """Patch requests.get and silence the inter-series sleep."""
        patcher = mock.patch(_requests_get, side_effect=side_effect)
        get_mock = patcher.start()
        self.addCleanup(patcher.stop)
        sleep_patcher = mock.patch(_file_ns + ".time.sleep")
        self.sleep_mock = sleep_patcher.start()
        self.addCleanup(sleep_patcher.stop)
        return get_mock

    # ---------------------------------------------------------- URL format

    def test_series_comes_before_dates(self):
        """The range URL is /Observations/<series>/<from>/<to>."""
        get_mock = self._patch_get(lambda url, timeout: FakeResponse(
            payload=[{"date": "2026-11-20", "value": 11.2125}]
        ))
        self.provider._obtain_rates(
            "SEK", ["EUR"], date(2026, 11, 17), date(2026, 11, 21)
        )
        url = get_mock.call_args_list[0][0][0]
        self.assertEqual(
            url,
            "https://api.riksbank.se/swea/v1/Observations/SEKEURPMI"
            "/2026-11-17/2026-11-21",
        )

    def test_latest_url_for_single_day(self):
        get_mock = self._patch_get(lambda url, timeout: FakeResponse(
            payload={"date": "2026-11-24", "value": 11.221}
        ))
        self.provider._obtain_rates(
            "SEK", ["EUR"], date(2026, 11, 24), date(2026, 11, 24)
        )
        url = get_mock.call_args_list[0][0][0]
        self.assertEqual(
            url,
            "https://api.riksbank.se/swea/v1/Observations/Latest/SEKEURPMI",
        )

    def test_one_request_per_currency(self):
        """A comma separated series list is rejected by Riksbank."""
        get_mock = self._patch_get(lambda url, timeout: FakeResponse(
            payload=[{"date": "2026-11-20", "value": 11.2125}]
        ))
        self.provider._obtain_rates(
            "SEK", ["EUR", "USD"], date(2026, 11, 17), date(2026, 11, 21)
        )
        urls = [call[0][0] for call in get_mock.call_args_list]
        self.assertEqual(len(urls), 2)
        self.assertIn("SEKEURPMI", urls[0])
        self.assertIn("SEKUSDPMI", urls[1])
        for url in urls:
            self.assertNotIn(",", url)

    # ------------------------------------------------------- rate direction

    def test_rate_is_inverted(self):
        """Riksbank gives SEK per EUR; res.currency.rate stores the inverse."""
        self._patch_get(lambda url, timeout: FakeResponse(
            payload=[{"date": "2026-11-20", "value": 11.2125}]
        ))
        rates = self.provider._obtain_rates(
            "SEK", ["EUR"], date(2026, 11, 17), date(2026, 11, 21)
        )
        self.assertAlmostEqual(rates["2026-11-20"]["EUR"], 1 / 11.2125)

    def test_inverted_rate_matches_odoo_convention(self):
        """1 / 11.2375 is the value Odoo stores for EUR on 2026-11-23."""
        self._patch_get(lambda url, timeout: FakeResponse(
            payload={"date": "2026-11-23", "value": 11.2375}
        ))
        rates = self.provider._obtain_rates(
            "SEK", ["EUR"], date(2026, 11, 23), date(2026, 11, 23)
        )
        self.assertEqual(rates["2026-11-23"]["EUR"], 1 / 11.2375)
        self.assertAlmostEqual(
            rates["2026-11-23"]["EUR"], 0.0889877641824249, places=15
        )

    def test_base_currency_is_not_fetched(self):
        self._patch_get(lambda url, timeout: FakeResponse(
            payload=[{"date": "2026-11-20", "value": 11.2125}]
        ))
        rates = self.provider._obtain_rates(
            "SEK", ["SEK", "EUR"], date(2026, 11, 17), date(2026, 11, 21)
        )
        self.assertNotIn("SEK", rates["2026-11-20"])

    def test_unsupported_currency_is_skipped(self):
        get_mock = self._patch_get(lambda url, timeout: FakeResponse(
            payload=[{"date": "2026-11-20", "value": 11.2125}]
        ))
        rates = self.provider._obtain_rates(
            "SEK", ["EUR", "XYZ"], date(2026, 11, 17), date(2026, 11, 21)
        )
        self.assertEqual(len(get_mock.call_args_list), 1)
        self.assertEqual(list(rates["2026-11-20"]), ["EUR"])

    # ----------------------------------------------------------- rate limit

    def test_sleep_between_series(self):
        self._patch_get(lambda url, timeout: FakeResponse(
            payload=[{"date": "2026-11-20", "value": 11.2125}]
        ))
        self.provider._obtain_rates(
            "SEK", ["EUR", "USD"], date(2026, 11, 17), date(2026, 11, 21)
        )
        self.assertEqual(self.sleep_mock.call_count, 1)
        self.assertEqual(self.sleep_mock.call_args[0][0], 8)

    def test_retry_after_429_uses_hint(self):
        responses = [
            FakeResponse(
                status_code=429,
                payload={
                    "statusCode": 429,
                    "message": "Rate limit is exceeded. Try again in 7 seconds.",
                },
            ),
            FakeResponse(payload=[{"date": "2026-11-20", "value": 11.2125}]),
        ]
        get_mock = self._patch_get(lambda url, timeout: responses.pop(0))
        rates = self.provider._obtain_rates(
            "SEK", ["EUR"], date(2026, 11, 17), date(2026, 11, 21)
        )
        self.assertEqual(get_mock.call_count, 2)
        self.assertEqual(self.sleep_mock.call_args[0][0], 7)
        self.assertIn("EUR", rates["2026-11-20"])

    def test_429_without_hint_uses_default_delay(self):
        responses = [
            FakeResponse(status_code=429, payload={"statusCode": 429}),
            FakeResponse(payload=[{"date": "2026-11-20", "value": 11.2125}]),
        ]
        self._patch_get(lambda url, timeout: responses.pop(0))
        self.provider._obtain_rates(
            "SEK", ["EUR"], date(2026, 11, 17), date(2026, 11, 21)
        )
        self.assertEqual(self.sleep_mock.call_args[0][0], 10)

    def test_429_gives_up_after_three_attempts(self):
        get_mock = self._patch_get(lambda url, timeout: FakeResponse(
            status_code=429,
            payload={"statusCode": 429, "message": "Try again in 5 seconds."},
        ))
        with self.assertRaises(UserError):
            self.provider._obtain_rates(
                "SEK", ["EUR"], date(2026, 11, 17), date(2026, 11, 21)
            )
        self.assertEqual(get_mock.call_count, 3)

    def test_http_error_raises(self):
        self._patch_get(lambda url, timeout: FakeResponse(status_code=400))
        with self.assertRaises(UserError):
            self.provider._obtain_rates(
                "SEK", ["EUR"], date(2026, 11, 17), date(2026, 11, 21)
            )

    # -------------------------------------------------------------- weekend

    def test_weekend_days_are_absent(self):
        """Riksbank publishes nothing on Saturday and Sunday."""
        self._patch_get(lambda url, timeout: FakeResponse(
            payload=[
                {"date": "2026-11-20", "value": 11.2125},
                {"date": "2026-11-23", "value": 11.221},
            ]
        ))
        # 2026-11-21 and 2026-11-22 are Saturday and Sunday.
        rates = self.provider._obtain_rates(
            "SEK", ["EUR"], date(2026, 11, 20), date(2026, 11, 23)
        )
        self.assertEqual(sorted(rates), ["2026-11-20", "2026-11-23"])

    def test_weekend_only_range_returns_empty(self):
        self._patch_get(lambda url, timeout: FakeResponse(payload=[]))
        rates = self.provider._obtain_rates(
            "SEK", ["EUR"], date(2026, 11, 21), date(2026, 11, 22)
        )
        self.assertEqual(rates, {})

    def test_null_value_is_skipped(self):
        self._patch_get(lambda url, timeout: FakeResponse(
            payload=[{"date": "2026-11-20", "value": None}]
        ))
        rates = self.provider._obtain_rates(
            "SEK", ["EUR"], date(2026, 11, 17), date(2026, 11, 21)
        )
        self.assertEqual(rates, {})

    # ------------------------------------------------------------- provider

    def test_supported_currencies(self):
        currencies = self.provider._get_supported_currencies()
        self.assertIn("EUR", currencies)
        self.assertIn("USD", currencies)
        self.assertNotIn("SEK", currencies)

    def test_other_service_delegates_to_super(self):
        ecb = self.Provider.create({
            "company_id": self.company.id,
            "service": "ECB",
            "currency_ids": [(6, 0, [self.env.ref("base.EUR").id])],
        })
        self.assertNotIn("SEK", ecb._get_supported_currencies())

    def test_update_writes_res_currency_rate(self):
        """The provider stores the inverse rate on the observation date."""
        self._patch_get(lambda url, timeout: FakeResponse(
            payload=[{"date": "2026-11-20", "value": 11.2125}]
        ))
        eur = self.env.ref("base.EUR")
        self.env["res.currency.rate"].search([
            ("currency_id", "=", eur.id),
            ("company_id", "=", self.company.id),
        ]).unlink()
        self.provider._update(date(2026, 11, 17), date(2026, 11, 21))
        rate = self.env["res.currency.rate"].search([
            ("currency_id", "=", eur.id),
            ("company_id", "=", self.company.id),
            ("name", "=", date(2026, 11, 20)),
        ])
        self.assertTrue(rate)
        self.assertAlmostEqual(rate.rate, 1 / 11.2125)
        rate.unlink()

    def test_non_sek_company_currency_raises(self):
        company = self.env["res.company"].create({
            "name": "Riksbank EUR AB",
            "currency_id": self.env.ref("base.EUR").id,
        })
        provider = self.Provider.create({
            "company_id": company.id,
            "service": "riksbank",
            "currency_ids": [(6, 0, [self.env.ref("base.USD").id])],
        })
        with self.assertRaises(UserError):
            provider._obtain_rates(
                "XYZ", ["USD"], date(2026, 11, 17), date(2026, 11, 21)
            )
